import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  Archive,
  ArrowDownRight,
  ArrowUpRight,
  Calendar,
  CheckCircle2,
  Clock,
  Cloud,
  Database,
  Download,
  Edit2,
  ExternalLink,
  FileText,
  Filter,
  History,
  Info,
  Layers,
  Lock,
  LogOut,
  Mail,
  MapPin,
  MinusCircle,
  Package,
  Pill,
  Plus,
  PlusCircle,
  RefreshCw,
  Search,
  Server,
  ShieldAlert,
  Trash2,
  TrendingUp,
  User,
  X
} from 'lucide-react';

import api, { authService, medicineService, alertService, reportService } from './api';

export default function App() {
  // Authentication State
  const [currentUser, setCurrentUser] = useState(authService.getCurrentUser());
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'
  const [authFormData, setAuthFormData] = useState({
    name: 'City Care Pharmacy',
    email: 'admin@pharmacy.com',
    password: 'admin123',
    role: 'pharmacy'
  });
  const [authLoading, setAuthLoading] = useState(false);

  // Application State
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [medicines, setMedicines] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [usageTrends, setUsageTrends] = useState([]);
  const [healthInfo, setHealthInfo] = useState(null);

  // Filters & Search
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');

  // Modals state
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDispenseModal, setShowDispenseModal] = useState(false);
  const [showHealthModal, setShowHealthModal] = useState(false);

  // Selected Medicine for Modals
  const [selectedMed, setSelectedMed] = useState(null);
  const [dispenseAmount, setDispenseAmount] = useState(1);
  const [dispenseReason, setDispenseReason] = useState('Prescription Outpatient Sale');

  // Form State for Add / Edit
  const [formData, setFormData] = useState({
    name: '',
    batch_number: '',
    category: 'Analgesics & Antipyretics',
    quantity: 50,
    min_stock_level: 15,
    price: 10.00,
    expiry_date: '',
    supplier: ''
  });

  const [notification, setNotification] = useState(null);

  const showToast = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // Listen for 401 unauthorized session expiry events from api.js interceptor
  useEffect(() => {
    const handleUnauthorized = () => {
      setCurrentUser(null);
      showToast('Session expired. Please log in again.', 'danger');
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  // ===========================================================================
  // API Fetch Functions (Replacing Static/Dummy Data with Live Backend Calls)
  // ===========================================================================
  const loadDashboardData = async () => {
    if (!authService.isAuthenticated()) return;
    try {
      const [resSummary, resAlerts, resTrends, resHealth] = await Promise.all([
        reportService.getSummary(),
        alertService.getAlerts(),
        reportService.getUsageTrends(),
        api.get('/health').then(r => r.data).catch(() => null)
      ]);
      setStats(resSummary);
      setAlerts(resAlerts.alerts || []);
      setUsageTrends(resTrends.trends || []);
      setHealthInfo(resHealth);
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
    }
  };

  const loadMedicines = async () => {
    if (!authService.isAuthenticated()) return;
    setLoading(true);
    try {
      const data = await medicineService.getMedicines({
        search: search.trim(),
        category: categoryFilter,
        status: statusFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
        per_page: 50
      });
      setMedicines(data.medicines || []);
    } catch (err) {
      console.error('Failed to load medicines from backend:', err);
      showToast(err.response?.data?.error || 'Failed to fetch medicines', 'danger');
    } finally {
      setLoading(false);
    }
  };

  // Trigger data load when user logs in or filters change
  useEffect(() => {
    if (currentUser) {
      loadDashboardData();
      loadMedicines();
    }
  }, [currentUser]);

  useEffect(() => {
    if (currentUser) {
      loadMedicines();
    }
  }, [search, categoryFilter, statusFilter, sortBy, sortOrder]);

  // ===========================================================================
  // Authentication Handlers
  // ===========================================================================
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    try {
      if (authMode === 'login') {
        const res = await authService.login({
          email: authFormData.email,
          password: authFormData.password
        });
        setCurrentUser(res.user);
        showToast(`Welcome back, ${res.user.name}!`, 'success');
      } else {
        const res = await authService.register(authFormData);
        setCurrentUser(res.user);
        showToast(`Account created successfully!`, 'success');
      }
    } catch (err) {
      showToast(err.response?.data?.error || 'Authentication failed', 'danger');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    authService.logout();
    setCurrentUser(null);
    setMedicines([]);
    setStats(null);
    setAlerts([]);
    showToast('Logged out successfully', 'success');
  };

  // ===========================================================================
  // CRUD & Business Logic Handlers
  // ===========================================================================
  const handleAddMedicine = async (e) => {
    e.preventDefault();
    try {
      const res = await medicineService.createMedicine(formData);
      showToast(res.message || 'Medicine added successfully!', 'success');
      setShowAddModal(false);
      resetForm();
      loadMedicines();
      loadDashboardData();
    } catch (err) {
      showToast(err.response?.data?.error || 'Failed to add medicine', 'danger');
    }
  };

  const handleEditMedicine = async (e) => {
    e.preventDefault();
    if (!selectedMed) return;
    try {
      const res = await medicineService.updateMedicine(selectedMed.id, formData);
      showToast(res.message || 'Medicine updated successfully!', 'success');
      setShowEditModal(false);
      loadMedicines();
      loadDashboardData();
    } catch (err) {
      showToast(err.response?.data?.error || 'Failed to update medicine', 'danger');
    }
  };

  const handleDeleteMedicine = async (med) => {
    if (!window.confirm(`Are you sure you want to delete ${med.name} (Batch: ${med.batch_number})?`)) return;
    try {
      const res = await medicineService.deleteMedicine(med.id);
      showToast(res.message || 'Deleted successfully', 'success');
      loadMedicines();
      loadDashboardData();
    } catch (err) {
      showToast(err.response?.data?.error || 'Failed to delete medicine', 'danger');
    }
  };

  const handleDispense = async (e) => {
    e.preventDefault();
    if (!selectedMed) return;
    try {
      const res = await medicineService.useMedicine(selectedMed.id, {
        quantity_used: Number(dispenseAmount),
        note: dispenseReason
      });
      showToast(res.message || 'Dispensed successfully', 'success');
      setShowDispenseModal(false);
      loadMedicines();
      loadDashboardData();
    } catch (err) {
      showToast(err.response?.data?.error || 'Dispense failed', 'danger');
    }
  };

  const handleMarkAlertRead = async (alertId) => {
    try {
      await alertService.markAlertRead(alertId);
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_read: true } : a));
      showToast('Alert marked as read', 'success');
    } catch (err) {
      showToast('Failed to mark alert as read', 'danger');
    }
  };

  const handleMarkAllAlertsRead = async () => {
    try {
      await alertService.markAllAlertsRead();
      setAlerts(prev => prev.map(a => ({ ...a, is_read: true })));
      showToast('All alerts marked as read', 'success');
    } catch (err) {
      showToast('Failed to mark all alerts as read', 'danger');
    }
  };

  const handleExportCSV = async () => {
    try {
      await reportService.downloadExportCSV();
      showToast('Export downloaded successfully!', 'success');
    } catch (err) {
      showToast('Failed to export CSV report', 'danger');
    }
  };

  const handleTriggerAuditCheck = async () => {
    try {
      const res = await alertService.triggerAuditCheck();
      showToast(res.message || 'Audit check executed', 'success');
      loadDashboardData();
    } catch (err) {
      showToast('Failed to run audit check', 'danger');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      batch_number: '',
      category: 'Analgesics & Antipyretics',
      quantity: 50,
      min_stock_level: 15,
      price: 10.00,
      expiry_date: '',
      supplier: ''
    });
  };

  const openEdit = (med) => {
    setSelectedMed(med);
    setFormData({
      name: med.name,
      batch_number: med.batch_number,
      category: med.category,
      quantity: med.quantity,
      min_stock_level: med.min_stock_level,
      price: med.price,
      expiry_date: med.expiry_date,
      supplier: med.supplier || ''
    });
    setShowEditModal(true);
  };

  const openDispense = (med) => {
    setSelectedMed(med);
    setDispenseAmount(1);
    setDispenseReason('Prescription Outpatient Sale');
    setShowDispenseModal(true);
  };

  const categories = [
    'Analgesics & Antipyretics',
    'Antibiotics',
    'Antidiabetic',
    'Cardiovascular',
    'Antihistamines & Allergy',
    'Gastrointestinal',
    'Respiratory',
    'Ophthalmic',
    'Vitamins & Supplements',
    'Dermatological'
  ];

  // ===========================================================================
  // Render Login View if Not Authenticated
  // ===========================================================================
  if (!currentUser) {
    return (
      <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%)', padding: '1rem' }}>
        {notification && (
          <div style={{
            position: 'fixed',
            top: '1.25rem',
            right: '1.25rem',
            zIndex: 100,
            background: notification.type === 'danger' ? '#ef4444' : '#10b981',
            color: 'white',
            padding: '0.85rem 1.4rem',
            borderRadius: '8px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.65rem',
            fontWeight: 600,
            fontSize: '0.9rem'
          }}>
            {notification.type === 'danger' ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
            <span>{notification.message}</span>
          </div>
        )}

        <div className="card" style={{ maxWidth: 440, width: '100%', padding: '2rem', borderRadius: 16, boxShadow: '0 20px 40px rgba(0,0,0,0.08)' }}>
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <div style={{
              width: 52,
              height: 52,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #0284c7 0%, #0d9488 100%)',
              color: 'white',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '0.75rem',
              boxShadow: '0 8px 16px rgba(2, 132, 199, 0.3)'
            }}>
              <Pill size={28} />
            </div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#0f172a' }}>Medicine Stock & Expiry Tracker</h2>
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.25rem' }}>
              Cloud Computing Project • NIE Mysore (Dept. of ISE)
            </p>
          </div>

          <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0', marginBottom: '1.5rem' }}>
            <button
              type="button"
              style={{
                flex: 1,
                padding: '0.75rem',
                border: 'none',
                background: 'none',
                fontWeight: 700,
                color: authMode === 'login' ? '#0284c7' : '#94a3b8',
                borderBottom: authMode === 'login' ? '2px solid #0284c7' : '2px solid transparent',
                cursor: 'pointer'
              }}
              onClick={() => setAuthMode('login')}
            >
              Sign In
            </button>
            <button
              type="button"
              style={{
                flex: 1,
                padding: '0.75rem',
                border: 'none',
                background: 'none',
                fontWeight: 700,
                color: authMode === 'register' ? '#0284c7' : '#94a3b8',
                borderBottom: authMode === 'register' ? '2px solid #0284c7' : '2px solid transparent',
                cursor: 'pointer'
              }}
              onClick={() => setAuthMode('register')}
            >
              Create Account
            </button>
          </div>

          <form onSubmit={handleAuthSubmit}>
            {authMode === 'register' && (
              <div className="form-group" style={{ marginBottom: '1rem' }}>
                <label className="form-label">Pharmacy or Individual Name</label>
                <div style={{ position: 'relative' }}>
                  <User size={16} style={{ position: 'absolute', left: 10, top: 11, color: '#94a3b8' }} />
                  <input
                    type="text"
                    required
                    className="form-control"
                    placeholder="e.g. City Care Pharmacy"
                    value={authFormData.name}
                    onChange={(e) => setAuthFormData({ ...authFormData, name: e.target.value })}
                    style={{ paddingLeft: '2rem' }}
                  />
                </div>
              </div>
            )}

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label">Email Address</label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} style={{ position: 'absolute', left: 10, top: 11, color: '#94a3b8' }} />
                <input
                  type="email"
                  required
                  className="form-control"
                  placeholder="name@pharmacy.com"
                  value={authFormData.email}
                  onChange={(e) => setAuthFormData({ ...authFormData, email: e.target.value })}
                  style={{ paddingLeft: '2rem' }}
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label className="form-label">Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} style={{ position: 'absolute', left: 10, top: 11, color: '#94a3b8' }} />
                <input
                  type="password"
                  required
                  className="form-control"
                  placeholder="••••••••"
                  value={authFormData.password}
                  onChange={(e) => setAuthFormData({ ...authFormData, password: e.target.value })}
                  style={{ paddingLeft: '2rem' }}
                />
              </div>
            </div>

            {authMode === 'register' && (
              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label className="form-label">Account Role</label>
                <select
                  className="form-control"
                  value={authFormData.role}
                  onChange={(e) => setAuthFormData({ ...authFormData, role: e.target.value })}
                >
                  <option value="pharmacy">Pharmacy / Hospital Dispensary</option>
                  <option value="individual">Individual / Home Medical Care</option>
                </select>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={authLoading}
              style={{ width: '100%', padding: '0.75rem', fontSize: '0.95rem' }}
            >
              {authLoading ? 'Authenticating...' : (authMode === 'login' ? 'Sign In to Dashboard' : 'Register Account')}
            </button>
          </form>

          {authMode === 'login' && (
            <div style={{ marginTop: '1.25rem', padding: '0.85rem', background: '#f8fafc', borderRadius: 8, fontSize: '0.8rem', color: '#64748b', border: '1px dashed #cbd5e1' }}>
              <strong>Demo Credentials (Pre-seeded):</strong>
              <div>Email: <code>admin@pharmacy.com</code></div>
              <div>Password: <code>admin123</code></div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ===========================================================================
  // Main Authenticated Application View
  // ===========================================================================
  return (
    <div className="app-container">
      {/* Toast Notification */}
      {notification && (
        <div style={{
          position: 'fixed',
          top: '1.25rem',
          right: '1.25rem',
          zIndex: 100,
          background: notification.type === 'danger' ? '#ef4444' : '#10b981',
          color: 'white',
          padding: '0.85rem 1.4rem',
          borderRadius: '8px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.65rem',
          fontWeight: 600,
          fontSize: '0.9rem'
        }}>
          {notification.type === 'danger' ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Top Navbar */}
      <header className="navbar">
        <div className="nav-inner">
          <div className="brand">
            <div className="brand-icon">
              <Pill size={24} />
            </div>
            <div>
              <div className="brand-title">Medicine Stock & Expiry Tracker</div>
              <div className="brand-subtitle">
                Logged in as <strong>{currentUser.name}</strong> ({currentUser.role})
              </div>
            </div>
          </div>

          <div className="nav-actions">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setShowHealthModal(true)}
              title="Cloud System Status"
            >
              <span style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: '#10b981',
                display: 'inline-block'
              }} />
              <span>Cloud Status</span>
            </button>

            <button
              className="btn btn-secondary btn-sm"
              onClick={handleExportCSV}
              title="Export complete inventory to CSV"
            >
              <Download size={15} />
              <span>Export CSV</span>
            </button>

            <button
              className="btn btn-secondary btn-sm"
              onClick={handleTriggerAuditCheck}
              title="Execute APScheduler stock check now"
            >
              <RefreshCw size={15} />
              <span>Run Audit</span>
            </button>

            <button
              className="btn btn-primary"
              onClick={() => { resetForm(); setShowAddModal(true); }}
            >
              <Plus size={16} />
              <span>Add Medicine</span>
            </button>

            <button
              className="btn btn-secondary btn-sm"
              onClick={handleLogout}
              title="Sign Out"
              style={{ color: '#dc2626' }}
            >
              <LogOut size={15} />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="tabs-container">
        <div className="tabs-inner">
          <button
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <Layers size={17} />
            <span>Dashboard & Analytics</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'inventory' ? 'active' : ''}`}
            onClick={() => setActiveTab('inventory')}
          >
            <Package size={17} />
            <span>Medicine Inventory</span>
            <span style={{ background: '#e2e8f0', color: '#334155', padding: '0.1rem 0.45rem', borderRadius: 9999, fontSize: '0.72rem' }}>
              {medicines.length}
            </span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'alerts' ? 'active' : ''}`}
            onClick={() => setActiveTab('alerts')}
          >
            <AlertTriangle size={17} />
            <span>Alerts & Notifications</span>
            {alerts.filter(a => !a.is_read).length > 0 && (
              <span className="tab-badge">{alerts.filter(a => !a.is_read).length}</span>
            )}
          </button>

          <button
            className={`nav-tab ${activeTab === 'trends' ? 'active' : ''}`}
            onClick={() => setActiveTab('trends')}
          >
            <TrendingUp size={17} />
            <span>Usage Trends</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'cloud' ? 'active' : ''}`}
            onClick={() => setActiveTab('cloud')}
          >
            <Cloud size={17} />
            <span>Cloud Architecture</span>
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        {/* ===================================================================
            TAB 1: DASHBOARD & METRICS
        =================================================================== */}
        {activeTab === 'dashboard' && stats && (
          <div>
            <div className="kpi-grid">
              <div className="kpi-card">
                <div>
                  <div className="kpi-label">Total Medicines</div>
                  <div className="kpi-value">{stats.total_medicines}</div>
                  <div className="kpi-meta">{stats.total_units} units in stock</div>
                </div>
                <div className="kpi-icon-box" style={{ background: '#e0f2fe', color: '#0284c7' }}>
                  <Package size={24} />
                </div>
              </div>

              <div className="kpi-card">
                <div>
                  <div className="kpi-label">Total Inventory Value</div>
                  <div className="kpi-value">₹{stats.total_valuation.toLocaleString()}</div>
                  <div className="kpi-meta">Scoped to {currentUser.name}</div>
                </div>
                <div className="kpi-icon-box" style={{ background: '#dcfce7', color: '#16a34a' }}>
                  <TrendingUp size={24} />
                </div>
              </div>

              <div className="kpi-card" style={{ borderLeft: '4px solid #ef4444' }}>
                <div>
                  <div className="kpi-label">Expired Medicines</div>
                  <div className="kpi-value" style={{ color: '#dc2626' }}>{stats.expired_count}</div>
                  <div className="kpi-meta">Requires disposal/quarantine</div>
                </div>
                <div className="kpi-icon-box" style={{ background: '#fee2e2', color: '#dc2626' }}>
                  <ShieldAlert size={24} />
                </div>
              </div>

              <div className="kpi-card" style={{ borderLeft: '4px solid #f97316' }}>
                <div>
                  <div className="kpi-label">Expiring in 30 Days</div>
                  <div className="kpi-value" style={{ color: '#ea580c' }}>{stats.expiring_count}</div>
                  <div className="kpi-meta">FEFO priority dispatch</div>
                </div>
                <div className="kpi-icon-box" style={{ background: '#ffedd5', color: '#ea580c' }}>
                  <Clock size={24} />
                </div>
              </div>

              <div className="kpi-card" style={{ borderLeft: '4px solid #eab308' }}>
                <div>
                  <div className="kpi-label">Low Stock Alerts</div>
                  <div className="kpi-value" style={{ color: '#ca8a04' }}>{stats.low_stock_count}</div>
                  <div className="kpi-meta">{stats.out_of_stock_count} completely depleted</div>
                </div>
                <div className="kpi-icon-box" style={{ background: '#fef9c3', color: '#ca8a04' }}>
                  <AlertTriangle size={24} />
                </div>
              </div>
            </div>

            {/* Unread Alerts Banner */}
            {alerts.filter(a => !a.is_read).length > 0 && (
              <div className="card" style={{ border: '1px solid #fecaca', background: '#fff5f5' }}>
                <div className="card-header" style={{ background: 'transparent', borderBottom: '1px solid #fecaca' }}>
                  <div className="card-title" style={{ color: '#b91c1c' }}>
                    <ShieldAlert size={20} />
                    <span>Unread Inventory Alerts ({alerts.filter(a => !a.is_read).length})</span>
                  </div>
                  <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('alerts')}>
                    View All &rarr;
                  </button>
                </div>
                <div className="card-body">
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '0.85rem' }}>
                    {alerts.filter(a => !a.is_read).slice(0, 3).map((alert) => (
                      <div key={alert.id} style={{
                        background: '#ffffff',
                        padding: '1rem',
                        borderRadius: '8px',
                        border: '1px solid #fee2e2',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        gap: '0.5rem'
                      }}>
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#991b1b' }}>{alert.medicine_name}</span>
                            <span className={`badge ${alert.type === 'expired' ? 'badge-critical' : 'badge-warning'}`}>
                              {alert.type.toUpperCase()}
                            </span>
                          </div>
                          <p style={{ fontSize: '0.8rem', color: '#4b5563', marginTop: '0.35rem' }}>{alert.message}</p>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid #f3f4f6' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleMarkAlertRead(alert.id)}
                          >
                            Mark Read
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Category Breakdown */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <Archive size={18} />
                  <span>Category Distribution</span>
                </div>
              </div>
              <div className="card-body">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
                  {stats.category_breakdown.map((cat, idx) => {
                    const percentage = Math.round((cat.units / (stats.total_units || 1)) * 100);
                    return (
                      <div key={idx}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                          <span style={{ fontWeight: 600 }}>{cat.category}</span>
                          <span style={{ color: '#64748b' }}>
                            {cat.count} meds • {cat.units} units • <strong>₹{cat.value.toLocaleString()}</strong>
                          </span>
                        </div>
                        <div style={{ width: '100%', height: '8px', background: '#f1f5f9', borderRadius: '9999px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${percentage}%`,
                            height: '100%',
                            background: '#0284c7',
                            borderRadius: '9999px'
                          }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ===================================================================
            TAB 2: MEDICINE INVENTORY CATALOG
        =================================================================== */}
        {activeTab === 'inventory' && (
          <div>
            {/* Filter Bar */}
            <div className="card" style={{ marginBottom: '1.25rem' }}>
              <div className="card-body" style={{ padding: '1rem 1.25rem' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
                  {/* Search */}
                  <div style={{ position: 'relative', flex: '1 1 240px' }}>
                    <Search size={16} style={{ position: 'absolute', left: 10, top: 11, color: '#94a3b8' }} />
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Search medicine name, batch, supplier..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      style={{ paddingLeft: '2rem' }}
                    />
                  </div>

                  {/* Category Filter */}
                  <select
                    className="form-control"
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    style={{ flex: '0 1 200px' }}
                  >
                    <option value="">All Categories</option>
                    {categories.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>

                  {/* Status Filter */}
                  <select
                    className="form-control"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    style={{ flex: '0 1 170px' }}
                  >
                    <option value="">All Statuses</option>
                    <option value="expired">Expired</option>
                    <option value="expiring">Expiring (&lt; 30d)</option>
                    <option value="low_stock">Low Stock</option>
                    <option value="good">Good Stock</option>
                  </select>

                  {/* Sort By */}
                  <select
                    className="form-control"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    style={{ flex: '0 1 150px' }}
                  >
                    <option value="name">Sort: Name</option>
                    <option value="expiry_date">Sort: Expiry Date</option>
                    <option value="quantity">Sort: Quantity</option>
                    <option value="price">Sort: Price</option>
                  </select>

                  <button
                    className="btn btn-secondary btn-icon"
                    onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                    title={`Sort Order: ${sortOrder.toUpperCase()}`}
                  >
                    {sortOrder === 'asc' ? '▲' : '▼'}
                  </button>

                  {(search || categoryFilter || statusFilter) && (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setSearch('');
                        setCategoryFilter('');
                        setStatusFilter('');
                      }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Medicines Table */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <Package size={18} />
                  <span>Medicine Inventory Catalog ({medicines.length} items)</span>
                </div>
              </div>

              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Medicine Name</th>
                      <th>Batch No.</th>
                      <th>Category</th>
                      <th>Stock Quantity</th>
                      <th>Price</th>
                      <th>Expiry Date</th>
                      <th>Supplier</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan="8" style={{ textAlign: 'center', padding: '2.5rem' }}>
                          <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite' }} />
                          <p style={{ marginTop: '0.5rem', color: '#64748b' }}>Fetching medicine records...</p>
                        </td>
                      </tr>
                    ) : medicines.length === 0 ? (
                      <tr>
                        <td colSpan="8" style={{ textAlign: 'center', padding: '3rem' }}>
                          <Package size={36} style={{ color: '#cbd5e1', margin: '0 auto 0.75rem' }} />
                          <div style={{ fontWeight: 600, color: '#334155' }}>No medicines found</div>
                          <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                            Add your first medicine using the button above.
                          </p>
                        </td>
                      </tr>
                    ) : (
                      medicines.map((med) => (
                        <tr key={med.id}>
                          <td>
                            <div style={{ fontWeight: 700, color: '#0f172a' }}>{med.name}</div>
                          </td>
                          <td>
                            <span style={{
                              fontFamily: 'JetBrains Mono, monospace',
                              fontSize: '0.8rem',
                              background: '#f1f5f9',
                              padding: '0.2rem 0.45rem',
                              borderRadius: '4px'
                            }}>
                              {med.batch_number}
                            </span>
                          </td>
                          <td>
                            <div style={{ fontWeight: 500 }}>{med.category}</div>
                          </td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                              <span style={{
                                fontWeight: 700,
                                fontSize: '1rem',
                                color: med.quantity === 0 ? '#dc2626' : (med.is_low_stock ? '#d97706' : '#0f172a')
                              }}>
                                {med.quantity}
                              </span>
                              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                                / min {med.min_stock_level}
                              </span>
                            </div>
                            {med.is_low_stock && (
                              <span className="badge badge-warning" style={{ marginTop: '0.2rem' }}>
                                Low Stock
                              </span>
                            )}
                          </td>
                          <td>
                            <div style={{ fontWeight: 600 }}>₹{Number(med.price).toFixed(2)}</div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                              Val: ₹{(med.quantity * Number(med.price)).toLocaleString()}
                            </div>
                          </td>
                          <td>
                            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{med.expiry_date}</div>
                            <span className={`badge ${
                              med.status === 'expired' ? 'badge-critical' :
                              (med.status === 'expiring' ? 'badge-danger' : 'badge-safe')
                            }`}>
                              {med.status === 'expired' ? `Expired (${Math.abs(med.days_to_expiry)}d ago)` :
                              (med.status === 'expiring' ? `Expires in ${med.days_to_expiry}d` : `${med.days_to_expiry}d safe`)}
                            </span>
                          </td>
                          <td>
                            <div style={{ fontSize: '0.8rem', color: '#475569' }}>
                              {med.supplier || 'N/A'}
                            </div>
                          </td>
                          <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                            <div style={{ display: 'flex', gap: '0.35rem', justifyContent: 'flex-end' }}>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => openDispense(med)}
                                disabled={med.quantity === 0}
                                title="Dispense / Use Medicine"
                              >
                                <MinusCircle size={14} style={{ color: '#ef4444' }} />
                                <span>Use</span>
                              </button>

                              <button
                                className="btn btn-secondary btn-icon btn-sm"
                                onClick={() => openEdit(med)}
                                title="Edit Medicine"
                              >
                                <Edit2 size={14} />
                              </button>

                              <button
                                className="btn btn-secondary btn-icon btn-sm"
                                onClick={() => handleDeleteMedicine(med)}
                                title="Delete Medicine"
                              >
                                <Trash2 size={14} style={{ color: '#ef4444' }} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ===================================================================
            TAB 3: ALERTS & NOTIFICATIONS
        =================================================================== */}
        {activeTab === 'alerts' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div>
                <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>Active Stock & Expiry Alerts</h2>
                <p style={{ color: '#64748b', fontSize: '0.85rem' }}>
                  APScheduler audits your inventory daily and generates warnings for low-stock and expiring items.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-secondary btn-sm" onClick={handleMarkAllAlertsRead}>
                  Mark All Read
                </button>
                <button className="btn btn-secondary btn-sm" onClick={loadDashboardData}>
                  <RefreshCw size={14} />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {alerts.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '3.5rem' }}>
                <CheckCircle2 size={48} style={{ color: '#10b981', margin: '0 auto 1rem' }} />
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0f172a' }}>Zero Inventory Alerts!</h3>
                <p style={{ color: '#64748b', maxWidth: 450, margin: '0.5rem auto 0' }}>
                  All items in your medicine inventory are above reorder thresholds and well within valid shelf-life.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                {alerts.map((alert) => (
                  <div key={alert.id} className={`alert-card ${alert.type === 'expired' ? 'critical' : (alert.type === 'expiring' ? 'danger' : 'warning')}`} style={{ opacity: alert.is_read ? 0.65 : 1 }}>
                    <div style={{
                      padding: '0.65rem',
                      borderRadius: '8px',
                      background: alert.type === 'expired' ? '#fee2e2' : '#fef3c7',
                      color: alert.type === 'expired' ? '#dc2626' : '#d97706',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: 'fit-content'
                    }}>
                      <ShieldAlert size={22} />
                    </div>

                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>{alert.medicine_name}</h4>
                            <span className={`badge ${alert.type === 'expired' ? 'badge-critical' : 'badge-warning'}`}>
                              {alert.type.toUpperCase()}
                            </span>
                            {alert.is_read && <span className="badge badge-neutral">Read</span>}
                          </div>
                          <p style={{ fontSize: '0.85rem', color: '#4b5563', marginTop: '0.25rem' }}>{alert.message}</p>
                        </div>

                        {!alert.is_read && (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleMarkAlertRead(alert.id)}
                          >
                            Mark Read
                          </button>
                        )}
                      </div>

                      <div style={{
                        marginTop: '0.5rem',
                        paddingTop: '0.5rem',
                        borderTop: '1px solid rgba(0,0,0,0.06)',
                        fontSize: '0.75rem',
                        color: '#6b7280'
                      }}>
                        Generated on: {new Date(alert.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ===================================================================
            TAB 4: USAGE TRENDS & CHARTS
        =================================================================== */}
        {activeTab === 'trends' && (
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <TrendingUp size={18} />
                <span>Monthly Medicine Dispensing Trends (Past 6 Months)</span>
              </div>
            </div>
            <div className="card-body">
              <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '1.5rem' }}>
                Aggregate units consumed per month via <code>POST /api/medicines/&lt;id&gt;/use</code>:
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
                {usageTrends.map((t, idx) => (
                  <div key={idx} style={{
                    padding: '1.25rem',
                    background: '#f8fafc',
                    borderRadius: 10,
                    border: '1px solid #e2e8f0',
                    textAlign: 'center'
                  }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>{t.label}</div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#0284c7', margin: '0.35rem 0' }}>
                      {t.total_units_used}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                      {t.transaction_count} usage event(s)
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ===================================================================
            TAB 5: CLOUD ARCHITECTURE & SYNOPSIS
        =================================================================== */}
        {activeTab === 'cloud' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="card" style={{ background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)', border: '1px solid #bae6fd' }}>
              <div className="card-body">
                <span className="badge badge-neutral" style={{ background: '#0284c7', color: 'white', marginBottom: '0.5rem' }}>
                  ACADEMIC SYNOPSIS VERIFICATION
                </span>
                <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#0c4a6e' }}>
                  THE NATIONAL INSTITUTE OF ENGINEERING, MYSORE
                </h2>
                <p style={{ color: '#0369a1', fontWeight: 600 }}>Department of Information Science and Engineering • Cloud Computing</p>
                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #bae6fd', display: 'flex', gap: '2rem', flexWrap: 'wrap', fontSize: '0.85rem', color: '#0369a1' }}>
                  <div><strong>Student:</strong> Spoorthi K (4NI25IS438)</div>
                  <div><strong>Guide:</strong> Ms. Prajakta M, Assistant Professor</div>
                  <div><strong>Batch:</strong> D16 (Sec D)</div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <Server size={18} />
                  <span>Cloud API Telemetry & Tech Stack</span>
                </div>
              </div>
              <div className="card-body">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>BACKEND REST API</div>
                    <div style={{ fontWeight: 700 }}>Python Flask + Gunicorn</div>
                  </div>
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>DATABASE ORM</div>
                    <div style={{ fontWeight: 700 }}>MySQL (SQLAlchemy)</div>
                  </div>
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>AUTHENTICATION</div>
                    <div style={{ fontWeight: 700 }}>JWT + Bcrypt Hashing</div>
                  </div>
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>BACKGROUND SCHEDULER</div>
                    <div style={{ fontWeight: 700 }}>APScheduler (Daily Cron)</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ===================================================================
          MODALS
      =================================================================== */}
      {/* ADD MEDICINE MODAL */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Add New Medicine</h3>
              <button className="btn-icon" onClick={() => setShowAddModal(false)}><X size={18} /></button>
            </div>
            <form onSubmit={handleAddMedicine}>
              <div className="modal-body">
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label">Medicine Name *</label>
                    <input
                      type="text"
                      required
                      className="form-control"
                      placeholder="e.g. Paracetamol 650mg"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Batch Number *</label>
                    <input
                      type="text"
                      required
                      className="form-control"
                      placeholder="BATCH-2026-01"
                      value={formData.batch_number}
                      onChange={(e) => setFormData({ ...formData, batch_number: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Category *</label>
                    <select
                      className="form-control"
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    >
                      {categories.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Unit Price (₹) *</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      required
                      className="form-control"
                      value={formData.price}
                      onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) || 0 })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Initial Quantity *</label>
                    <input
                      type="number"
                      min="0"
                      required
                      className="form-control"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 0 })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Min Stock Level (Alert Threshold) *</label>
                    <input
                      type="number"
                      min="1"
                      required
                      className="form-control"
                      value={formData.min_stock_level}
                      onChange={(e) => setFormData({ ...formData, min_stock_level: parseInt(e.target.value) || 1 })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Expiry Date *</label>
                    <input
                      type="date"
                      required
                      className="form-control"
                      value={formData.expiry_date}
                      onChange={(e) => setFormData({ ...formData, expiry_date: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Supplier / Distributor</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. Cipla Ltd"
                      value={formData.supplier}
                      onChange={(e) => setFormData({ ...formData, supplier: e.target.value })}
                    />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save to Inventory</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT MEDICINE MODAL */}
      {showEditModal && selectedMed && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Edit Medicine Details</h3>
              <button className="btn-icon" onClick={() => setShowEditModal(false)}><X size={18} /></button>
            </div>
            <form onSubmit={handleEditMedicine}>
              <div className="modal-body">
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label">Medicine Name</label>
                    <input
                      type="text"
                      required
                      className="form-control"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Batch Number</label>
                    <input
                      type="text"
                      required
                      className="form-control"
                      value={formData.batch_number}
                      onChange={(e) => setFormData({ ...formData, batch_number: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Category</label>
                    <select
                      className="form-control"
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    >
                      {categories.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Unit Price (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      className="form-control"
                      value={formData.price}
                      onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) || 0 })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Current Stock Quantity</label>
                    <input
                      type="number"
                      min="0"
                      className="form-control"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 0 })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Min Stock Level Threshold</label>
                    <input
                      type="number"
                      min="1"
                      className="form-control"
                      value={formData.min_stock_level}
                      onChange={(e) => setFormData({ ...formData, min_stock_level: parseInt(e.target.value) || 1 })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Expiry Date</label>
                    <input
                      type="date"
                      required
                      className="form-control"
                      value={formData.expiry_date}
                      onChange={(e) => setFormData({ ...formData, expiry_date: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Supplier</label>
                    <input
                      type="text"
                      className="form-control"
                      value={formData.supplier}
                      onChange={(e) => setFormData({ ...formData, supplier: e.target.value })}
                    />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Update Medicine</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DISPENSE / USE MEDICINE MODAL */}
      {showDispenseModal && selectedMed && (
        <div className="modal-overlay" onClick={() => setShowDispenseModal(false)}>
          <div className="modal-content" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Dispense / Use Medicine</h3>
              <button className="btn-icon" onClick={() => setShowDispenseModal(false)}><X size={18} /></button>
            </div>
            <form onSubmit={handleDispense}>
              <div className="modal-body">
                <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: 8, marginBottom: '1rem', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{selectedMed.name}</div>
                  <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Batch: {selectedMed.batch_number}</div>
                  <div style={{ marginTop: '0.4rem', fontWeight: 600, color: '#0284c7' }}>
                    Available Stock: {selectedMed.quantity} units (Threshold: {selectedMed.min_stock_level})
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label">Units to Dispense / Use *</label>
                  <input
                    type="number"
                    min="1"
                    max={selectedMed.quantity}
                    required
                    className="form-control"
                    value={dispenseAmount}
                    onChange={(e) => setDispenseAmount(Math.max(1, parseInt(e.target.value) || 1))}
                  />
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    Stock remaining after dispense: {Math.max(0, selectedMed.quantity - dispenseAmount)} units
                  </span>
                </div>

                <div className="form-group">
                  <label className="form-label">Usage Note / Reason *</label>
                  <input
                    type="text"
                    required
                    className="form-control"
                    placeholder="e.g. Outpatient Prescription #4421"
                    value={dispenseReason}
                    onChange={(e) => setDispenseReason(e.target.value)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowDispenseModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Confirm Dispense</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CLOUD HEALTH MODAL */}
      {showHealthModal && (
        <div className="modal-overlay" onClick={() => setShowHealthModal(false)}>
          <div className="modal-content" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Cloud size={20} style={{ color: '#0284c7' }} />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Cloud Backend Health</h3>
              </div>
              <button className="btn-icon" onClick={() => setShowHealthModal(false)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              {healthInfo ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: '#f8fafc', borderRadius: 6 }}>
                    <span style={{ color: '#64748b' }}>Service:</span>
                    <span style={{ fontWeight: 600 }}>{healthInfo.service}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: '#f8fafc', borderRadius: 6 }}>
                    <span style={{ color: '#64748b' }}>Database Tier:</span>
                    <span style={{ fontWeight: 600 }}>{healthInfo.database}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: '#f8fafc', borderRadius: 6 }}>
                    <span style={{ color: '#64748b' }}>Background Scheduler:</span>
                    <span className="badge badge-safe">{healthInfo.scheduler}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: '#f8fafc', borderRadius: 6 }}>
                    <span style={{ color: '#64748b' }}>Status:</span>
                    <span className="badge badge-safe">{healthInfo.status}</span>
                  </div>
                </div>
              ) : (
                <p>Loading telemetry...</p>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowHealthModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

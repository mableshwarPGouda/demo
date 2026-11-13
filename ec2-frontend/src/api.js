/**
 * Medicine Stock & Expiry Tracker - API Client
 * Axios instance with automatic JWT Authorization header injection,
 * 401 error interception, and helper methods for all backend REST endpoints.
 */

import axios from 'axios';

// Base API URL configured via VITE_API_URL or defaults to backend EC2 instance placeholder
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://<YOUR_BACKEND_EC2_PUBLIC_IP>:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// =============================================================================
// Axios Request Interceptor (Injects JWT Bearer Token)
// =============================================================================
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// =============================================================================
// Axios Response Interceptor (Handles 401 Unauthorized Session Expiration)
// =============================================================================
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      console.warn('Session expired or unauthorized request. Clearing auth credentials.');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      // Dispatch custom event so React components can respond cleanly without full page reloads
      window.dispatchEvent(new Event('auth:unauthorized'));
    }
    return Promise.reject(error);
  }
);

// =============================================================================
// 1. Authentication Endpoints
// =============================================================================
export const authService = {
  /**
   * Registers a new user account (pharmacy or individual).
   * @param {Object} userData - { name, email, password, role }
   */
  async register(userData) {
    const response = await api.post('/auth/register', userData);
    if (response.data.access_token) {
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  /**
   * Authenticates user credentials.
   * @param {Object} credentials - { email, password }
   */
  async login(credentials) {
    const response = await api.post('/auth/login', credentials);
    if (response.data.access_token) {
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  /**
   * Retrieves profile of currently authenticated user.
   */
  async getMe() {
    const response = await api.get('/auth/me');
    return response.data.user;
  },

  /**
   * Logs out the user by clearing local storage.
   */
  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.dispatchEvent(new Event('auth:logout'));
  },

  /**
   * Checks whether a valid session token exists in local storage.
   */
  isAuthenticated() {
    return !!localStorage.getItem('token');
  },

  /**
   * Returns current user object cached in local storage.
   */
  getCurrentUser() {
    try {
      const user = localStorage.getItem('user');
      return user ? JSON.parse(user) : null;
    } catch {
      return null;
    }
  }
};

// =============================================================================
// 2. Medicine Inventory Endpoints
// =============================================================================
export const medicineService = {
  /**
   * Fetches paginated list of medicines with search, category, and status filters.
   * @param {Object} params - { search, status, category, sort_by, sort_order, page, per_page }
   */
  async getMedicines(params = {}) {
    const response = await api.get('/medicines', { params });
    return response.data;
  },

  /**
   * Retrieves full details for a single medicine along with audit usage history.
   * @param {number} id
   */
  async getMedicineById(id) {
    const response = await api.get(`/medicines/${id}`);
    return response.data.medicine;
  },

  /**
   * Adds a new medicine item to inventory.
   * @param {Object} data - { name, batch_number, category, quantity, min_stock_level, price, expiry_date, supplier }
   */
  async createMedicine(data) {
    const response = await api.post('/medicines', data);
    return response.data;
  },

  /**
   * Updates an existing medicine item.
   * @param {number} id
   * @param {Object} data
   */
  async updateMedicine(id, data) {
    const response = await api.put(`/medicines/${id}`, data);
    return response.data;
  },

  /**
   * Deletes a medicine item from inventory.
   * @param {number} id
   */
  async deleteMedicine(id) {
    const response = await api.delete(`/medicines/${id}`);
    return response.data;
  },

  /**
   * Dispenses / consumes a quantity of medicine and logs the transaction.
   * @param {number} id - Medicine ID
   * @param {Object} usageData - { quantity_used, note }
   */
  async useMedicine(id, usageData) {
    const response = await api.post(`/medicines/${id}/use`, usageData);
    return response.data;
  }
};

// =============================================================================
// 3. Alerts & Notification Endpoints
// =============================================================================
export const alertService = {
  /**
   * Retrieves all alerts (low_stock, expiring, expired).
   * @param {Object} params - { unread_only: boolean }
   */
  async getAlerts(params = {}) {
    const response = await api.get('/alerts', { params });
    return response.data;
  },

  /**
   * Marks a single alert as read.
   * @param {number} id
   */
  async markAlertRead(id) {
    const response = await api.put(`/alerts/${id}/read`);
    return response.data;
  },

  /**
   * Marks all unread alerts for current user as read.
   */
  async markAllAlertsRead() {
    const response = await api.put('/alerts/read-all');
    return response.data;
  },

  /**
   * Manually triggers a stock and expiry audit run.
   */
  async triggerAuditCheck() {
    const response = await api.post('/alerts/trigger-check');
    return response.data;
  }
};

// =============================================================================
// 4. Reports & Analytics Endpoints
// =============================================================================
export const reportService = {
  /**
   * Retrieves high-level KPI metrics for the dashboard cards.
   */
  async getSummary() {
    const response = await api.get('/reports/summary');
    return response.data;
  },

  /**
   * Retrieves monthly usage trends across the past 6 months for chart rendering.
   */
  async getUsageTrends() {
    const response = await api.get('/reports/usage-trends');
    return response.data;
  },

  /**
   * Downloads inventory CSV export report directly in browser.
   */
  async downloadExportCSV() {
    const response = await api.get('/reports/export', {
      responseType: 'blob',
    });

    // Create a temporary anchor element to trigger download in user's browser
    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    const dateStr = new Date().toISOString().split('T')[0];
    link.href = url;
    link.setAttribute('download', `medicine_inventory_${dateStr}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }
};

// Default export of the axios instance
export default api;

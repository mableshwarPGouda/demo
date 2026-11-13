-- ==============================================================================
-- Medicine Stock & Expiry Tracker - MySQL Database Schema
-- Cloud Computing Academic Project (NIE Mysore - ISE)
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS medicine_tracker
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE medicine_tracker;

-- 1. Users Table (Authentication & Role Management)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('pharmacy', 'individual') NOT NULL DEFAULT 'pharmacy',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Medicines Table (Medicine Inventory & Stock Details)
CREATE TABLE IF NOT EXISTS medicines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    batch_number VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    min_stock_level INT NOT NULL DEFAULT 10,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    expiry_date DATE NOT NULL,
    supplier VARCHAR(150) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_medicine_user (user_id),
    INDEX idx_medicine_expiry (expiry_date),
    INDEX idx_medicine_quantity (quantity),
    INDEX idx_medicine_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Usage Logs Table (Audit Trail for Dispensing/Usage)
CREATE TABLE IF NOT EXISTS usage_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_id INT NOT NULL,
    quantity_used INT NOT NULL,
    used_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note TEXT NULL,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    INDEX idx_usage_medicine (medicine_id),
    INDEX idx_usage_date (used_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Alerts Table (Automated Expiry & Low-Stock Notifications)
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    medicine_id INT NOT NULL,
    type ENUM('low_stock', 'expiring', 'expired') NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    INDEX idx_alert_user (user_id),
    INDEX idx_alert_unread (user_id, is_read),
    INDEX idx_alert_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

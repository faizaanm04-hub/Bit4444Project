-- ===== FMZB Hub Module 1 - Users Database Schema =====

-- Drop existing tables if they exist (for fresh setup)
DROP TABLE IF EXISTS UserActivityLog;
DROP TABLE IF EXISTS UserProfile;

-- UserProfile Table
CREATE TABLE UserProfile (
    Email VARCHAR(100) PRIMARY KEY,
    UserType VARCHAR(20) NOT NULL CHECK (UserType IN ('customer', 'merchant')),
    ContactFirstName VARCHAR(50) NOT NULL,
    ContactLastName VARCHAR(50) NOT NULL,
    UPassword VARCHAR(255) NOT NULL,
    Phone VARCHAR(20) NULL,
    Website VARCHAR(100) NULL,
    BusinessName VARCHAR(100) NULL,
    Status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (Status IN ('active', 'disabled')),
    TimeOfCreation DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    LastLogin DATETIME NULL,
    INDEX idx_status (Status),
    INDEX idx_type (UserType),
    INDEX idx_created (TimeOfCreation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- UserActivityLog Table
CREATE TABLE UserActivityLog (
    AID INT AUTO_INCREMENT PRIMARY KEY,
    Email VARCHAR(100) NOT NULL,
    ActivityType VARCHAR(50) NOT NULL,
    ActivityDescription VARCHAR(255) NULL,
    ActivityDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Email) REFERENCES UserProfile(Email) ON DELETE CASCADE,
    INDEX idx_email (Email),
    INDEX idx_type (ActivityType),
    INDEX idx_date (ActivityDate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== SEED DATA FOR TESTING =====
-- Note: Passwords are hashed with werkzeug. These are examples of what would be hashed.
-- DO NOT use in production without proper password hashing.

-- Customer 1: John Smith (password: SecurePass123!)
INSERT INTO UserProfile (Email, UserType, ContactFirstName, ContactLastName, UPassword, Phone, Website, BusinessName, Status, TimeOfCreation, LastLogin)
VALUES ('john.customer@fmzb.com', 'customer', 'John', 'Smith', 'scrypt:32768:8:1$d0e9a5b2f3c7e9d2$a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6', '540-555-0101', NULL, NULL, 'active', NOW(), NULL);

-- Customer 2: Jane Doe (password: SecurePass456!)
INSERT INTO UserProfile (Email, UserType, ContactFirstName, ContactLastName, UPassword, Phone, Website, BusinessName, Status, TimeOfCreation, LastLogin)
VALUES ('jane.customer@fmzb.com', 'customer', 'Jane', 'Doe', 'scrypt:32768:8:1$e1f0a6c3f4d8e0d3$b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7', '540-555-0102', NULL, NULL, 'active', NOW(), NULL);

-- Merchant: Bob Johnson (password: SecurePass789!)
INSERT INTO UserProfile (Email, UserType, ContactFirstName, ContactLastName, UPassword, Phone, Website, BusinessName, Status, TimeOfCreation, LastLogin)
VALUES ('merchant@fmzb.com', 'merchant', 'Bob', 'Johnson', 'scrypt:32768:8:1$f2g1b7d4f5e9e1d4$c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8', '540-555-0103', 'https://bobshop.com', 'Bobs Online Store', 'active', NOW(), NULL);

-- Activity logs for seeded users
INSERT INTO UserActivityLog (Email, ActivityType, ActivityDescription, ActivityDate)
VALUES 
    ('john.customer@fmzb.com', 'Registered', 'Account created', DATE_SUB(NOW(), INTERVAL 5 DAY)),
    ('jane.customer@fmzb.com', 'Registered', 'Account created', DATE_SUB(NOW(), INTERVAL 3 DAY)),
    ('merchant@fmzb.com', 'Registered', 'Account created', DATE_SUB(NOW(), INTERVAL 1 DAY));

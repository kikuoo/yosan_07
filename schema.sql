CREATE DATABASE IF NOT EXISTS yosan_db;
USE yosan_db;

CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_code VARCHAR(50) NOT NULL,
    project_name VARCHAR(200) NOT NULL,
    contract_amount DECIMAL(12, 0) NOT NULL,
    budget_amount DECIMAL(12, 0) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_type_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    contractor TEXT NOT NULL,
    description TEXT NOT NULL,
    payment_type TEXT NOT NULL,  -- 請負 or 請負外
    amount INTEGER NOT NULL,
    FOREIGN KEY (work_type_id) REFERENCES work_types(id)
); 
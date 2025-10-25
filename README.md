# 🔍 Oracle Openflow Connector Configuration Verifier

[![Snowflake](https://img.shields.io/badge/Snowflake-Streamlit-blue)](https://docs.snowflake.com/en/user-guide/ui-streamlit)
[![Oracle](https://img.shields.io/badge/Oracle-19c%20%7C%2021c%20%7C%2023c-red)](https://www.oracle.com/database/)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **Snowflake Streamlit** application that verifies Oracle database configuration for the **Snowflake Openflow Connector**. Ensures your Oracle database is properly configured for Change Data Capture (CDC) operations.

## ✨ Features

- **Database Verification**: Archive log mode, supplemental logging, CDB status
- **User Management**: Required users (C##XSTREAMADMIN, C##CONNECTUSER) with privileges
- **XStream Configuration**: Outbound servers, capture processes, and queues
- **Interactive Dashboard**: Real-time verification with visual status indicators
- **Export Reports**: JSON reports for documentation
- **Remediation Guides**: SQL scripts to fix configuration issues

## 🚀 Quick Start

### Prerequisites
- Snowflake account with ACCOUNTADMIN role
- Oracle database (19c, 21c, or 23c) with network access

### 1. Setup Snowflake External Access

```sql

USE ROLE ACCOUNTADMIN;

-- Step 1: Create database and schema
CREATE DATABASE IF NOT EXISTS OPENFLOW_APP;
CREATE SCHEMA IF NOT EXISTS OPENFLOW_APP.ORACLE_CONFIG_VERIFIER;

USE DATABASE OPENFLOW_APP;
USE SCHEMA ORACLE_CONFIG_VERIFIER;

-- Step 2: Create Oracle Network ruule

CREATE OR REPLACE NETWORK RULE oracle_docker_network_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('<your oracle ec2 machine ip>:1521'); 


CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION oracle_external_access_integration
  ALLOWED_NETWORK_RULES = (oracle_docker_network_rule)
 /* ALLOWED_AUTHENTICATION_SECRETS = (
    oracle_system_password,
    oracle_connectuser_password,
    oracle_xstreamadmin_password
  )*/
  ENABLED = TRUE
  COMMENT = 'External access for Oracle database connection from Streamlit';

DESC INTEGRATION oracle_external_access_integration;

GRANT USAGE ON INTEGRATION oracle_external_access_integration TO ROLE SYSADMIN;

```

### 2. Create Streamlit App use the snowsight for quick setup

[Create and deploy Streamlit apps using Snowsight](https://docs.snowflake.com/developer-guide/streamlit/create-streamlit-ui)

### 4. Access Application

```sql
SHOW STREAMLITS;
```

## 📋 Configuration

### Oracle Requirements
- Archive log mode enabled
- Supplemental logging (ALL COLUMNS recommended)
- Container Database (CDB) architecture
- Required users: `C##XSTREAMADMIN`, `C##CONNECTUSER`
- Required tablespaces: `XSTREAM_ADM_TBS`, `CONNECTUSER_TBS`

## 🔧 Usage

1. **Connect**: Use sidebar to select connection or enter details manually
2. **Verify**: Click "Run Verification" to start checks
3. **Review**: Check dashboard, users, XStream, and detailed reports
4. **Export**: Download JSON reports for documentation

## 🛠️ Troubleshooting

### Common Issues

**"No route to host" Error**
```sql
-- Update network rule with correct Oracle host
ALTER NETWORK RULE oracle_network_rule
  SET VALUE_LIST = ('your-oracle-host:1521');
```

**"Access denied" for Secrets**
```sql
-- Grant access to your role
GRANT READ ON SECRET oracle_system_password TO ROLE <YOUR_ROLE>;
GRANT USAGE ON INTEGRATION oracle_external_access_integration TO ROLE <YOUR_ROLE>;
```

## 📁 Files

- `streamlit_app.py` - Main Streamlit application
- `oracle_connection_snowflake.py` - Oracle connection handler
- `oracle_config.json` - Connection configuration
- `snowflake_external_access_setup.sql` - Complete Snowflake setup script

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request


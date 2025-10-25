-- ============================================================================
-- Oracle Openflow Connector Configuration Verification Script
-- For use with SQL*Plus
-- ============================================================================
-- Purpose: Verify Oracle database is correctly configured for Snowflake
--          Openflow Connector
-- Usage:   sqlplus username/password@host:port/service @verify_oracle_config.sql
-- ============================================================================

SET ECHO OFF
SET FEEDBACK OFF
SET HEADING ON
SET PAGESIZE 1000
SET LINESIZE 200
SET VERIFY OFF
SET TIMING OFF
SET SERVEROUTPUT ON SIZE UNLIMITED

-- Clear screen and show header
CLEAR SCREEN

PROMPT
PROMPT ================================================================================
PROMPT   Oracle Openflow Connector Configuration Verification
PROMPT   Snowflake - Oracle CDC Setup Validator
PROMPT ================================================================================
PROMPT

-- Set container to CDB$ROOT
PROMPT Setting session container to CDB$ROOT...
PROMPT
ALTER SESSION SET CONTAINER = CDB$ROOT;
PROMPT Container set successfully.
PROMPT

PROMPT ================================================================================
PROMPT   SECTION 1: DATABASE CONFIGURATION
PROMPT ================================================================================
PROMPT

-- Check current container
PROMPT Current Container Context:
PROMPT --------------------------------------------------------------------------------
SELECT
   SYS_CONTEXT('USERENV', 'CON_NAME') as "Container Name",
   SYS_CONTEXT('USERENV', 'CON_ID') as "Container ID",
   SYS_CONTEXT('USERENV', 'CURRENT_USER') as "Current User"
FROM dual;

PROMPT
PROMPT Database Configuration:
PROMPT --------------------------------------------------------------------------------
COLUMN database_name FORMAT A20
COLUMN cdb FORMAT A5
COLUMN log_mode FORMAT A15
COLUMN force_logging FORMAT A15
COLUMN supp_log_min FORMAT A15 HEADING "Supp Log MIN"
COLUMN supp_log_all FORMAT A15 HEADING "Supp Log ALL"
COLUMN version FORMAT A80

SELECT
   name as database_name,
   cdb,
   log_mode,
   force_logging,
   supplemental_log_data_min as supp_log_min,
   supplemental_log_data_all as supp_log_all,
   (SELECT banner FROM v$version WHERE banner LIKE 'Oracle%') as version
FROM v$database;

PROMPT
PROMPT Configuration Checks:
PROMPT --------------------------------------------------------------------------------

DECLARE
   v_cdb VARCHAR2(10);
   v_log_mode VARCHAR2(20);
   v_supp_min VARCHAR2(10);
   v_supp_all VARCHAR2(10);
   v_total_checks NUMBER := 0;
   v_passed NUMBER := 0;
   v_failed NUMBER := 0;
   v_warnings NUMBER := 0;
BEGIN
   -- Get database info
   SELECT cdb, log_mode, supplemental_log_data_min, supplemental_log_data_all
   INTO v_cdb, v_log_mode, v_supp_min, v_supp_all
   FROM v$database;
  
   DBMS_OUTPUT.PUT_LINE('');
  
   -- Check 1: Archive Log Mode
   v_total_checks := v_total_checks + 1;
   IF v_log_mode = 'ARCHIVELOG' THEN
       DBMS_OUTPUT.PUT_LINE('✓ PASS: Archive Log Mode is ARCHIVELOG');
       v_passed := v_passed + 1;
   ELSE
       DBMS_OUTPUT.PUT_LINE('✗ FAIL: Archive Log Mode is ' || v_log_mode || ' (must be ARCHIVELOG)');
       DBMS_OUTPUT.PUT_LINE('        Remediation: SHUTDOWN IMMEDIATE; STARTUP MOUNT; ALTER DATABASE ARCHIVELOG; ALTER DATABASE OPEN;');
       v_failed := v_failed + 1;
   END IF;
  
   -- Check 2: Supplemental Logging
   v_total_checks := v_total_checks + 1;
   IF v_supp_all = 'YES' THEN
       DBMS_OUTPUT.PUT_LINE('✓ PASS: Full supplemental logging (ALL COLUMNS) is enabled');
       v_passed := v_passed + 1;
   ELSIF v_supp_min = 'YES' THEN
       DBMS_OUTPUT.PUT_LINE('✓ PASS: Minimal supplemental logging is enabled (consider upgrading to ALL COLUMNS)');
       DBMS_OUTPUT.PUT_LINE('        Recommendation: ALTER DATABASE ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;');
       v_passed := v_passed + 1;
   ELSE
       DBMS_OUTPUT.PUT_LINE('✗ FAIL: Supplemental logging is not enabled');
       DBMS_OUTPUT.PUT_LINE('        Remediation: ALTER DATABASE ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;');
       v_failed := v_failed + 1;
   END IF;
  
   -- Check 3: CDB
   v_total_checks := v_total_checks + 1;
   IF v_cdb = 'YES' THEN
       DBMS_OUTPUT.PUT_LINE('✓ PASS: Database is a Container Database (CDB)');
       v_passed := v_passed + 1;
   ELSE
       DBMS_OUTPUT.PUT_LINE('⚠ WARNING: Database is not a CDB (ensure proper configuration for non-CDB)');
       v_warnings := v_warnings + 1;
   END IF;
  
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('Database Configuration Summary: ' || v_passed || ' passed, ' || v_failed || ' failed, ' || v_warnings || ' warnings');
END;
/

PROMPT
PROMPT ================================================================================
PROMPT   SECTION 2: USER ACCOUNTS (Common Users)
PROMPT ================================================================================
PROMPT

PROMPT User Accounts Check:
PROMPT --------------------------------------------------------------------------------
COLUMN username FORMAT A30
COLUMN account_status FORMAT A20
COLUMN common FORMAT A10
COLUMN default_tablespace FORMAT A30
COLUMN created FORMAT A20

SELECT
   username,
   account_status,
   common,
   default_tablespace,
   TO_CHAR(created, 'YYYY-MM-DD HH24:MI:SS') as created
FROM cdb_users
WHERE username IN ('C##XSTREAMADMIN', 'C##CONNECTUSER')
ORDER BY username;

PROMPT
PROMPT User Status Checks:
PROMPT --------------------------------------------------------------------------------

DECLARE
   v_count NUMBER;
   v_status VARCHAR2(50);
   v_common VARCHAR2(10);
   v_total_checks NUMBER := 0;
   v_passed NUMBER := 0;
   v_failed NUMBER := 0;
BEGIN
   DBMS_OUTPUT.PUT_LINE('');
  
   -- Check C##XSTREAMADMIN
   v_total_checks := v_total_checks + 1;
   BEGIN
       SELECT account_status, common INTO v_status, v_common
       FROM cdb_users WHERE username = 'C##XSTREAMADMIN';
      
       IF v_status = 'OPEN' THEN
           DBMS_OUTPUT.PUT_LINE('✓ PASS: User C##XSTREAMADMIN exists and is OPEN (Common: ' || v_common || ')');
           v_passed := v_passed + 1;
       ELSE
           DBMS_OUTPUT.PUT_LINE('✗ FAIL: User C##XSTREAMADMIN is ' || v_status || ' (must be OPEN)');
           DBMS_OUTPUT.PUT_LINE('        Remediation: ALTER USER c##xstreamadmin ACCOUNT UNLOCK;');
           v_failed := v_failed + 1;
       END IF;
   EXCEPTION
       WHEN NO_DATA_FOUND THEN
           DBMS_OUTPUT.PUT_LINE('✗ FAIL: User C##XSTREAMADMIN does not exist');
           DBMS_OUTPUT.PUT_LINE('        Remediation: CREATE USER c##xstreamadmin IDENTIFIED BY password CONTAINER=ALL;');
           v_failed := v_failed + 1;
   END;
  
   -- Check C##CONNECTUSER
   v_total_checks := v_total_checks + 1;
   BEGIN
       SELECT account_status, common INTO v_status, v_common
       FROM cdb_users WHERE username = 'C##CONNECTUSER';
      
       IF v_status = 'OPEN' THEN
           DBMS_OUTPUT.PUT_LINE('✓ PASS: User C##CONNECTUSER exists and is OPEN (Common: ' || v_common || ')');
           v_passed := v_passed + 1;
       ELSE
           DBMS_OUTPUT.PUT_LINE('✗ FAIL: User C##CONNECTUSER is ' || v_status || ' (must be OPEN)');
           DBMS_OUTPUT.PUT_LINE('        Remediation: ALTER USER c##connectuser ACCOUNT UNLOCK;');
           v_failed := v_failed + 1;
       END IF;
   EXCEPTION
       WHEN NO_DATA_FOUND THEN
           DBMS_OUTPUT.PUT_LINE('✗ FAIL: User C##CONNECTUSER does not exist');
           DBMS_OUTPUT.PUT_LINE('        Remediation: CREATE USER c##connectuser IDENTIFIED BY password CONTAINER=ALL;');
           v_failed := v_failed + 1;
   END;
  
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('User Accounts Summary: ' || v_passed || ' passed, ' || v_failed || ' failed');
END;
/

PROMPT
PROMPT ================================================================================
PROMPT   SECTION 3: USER PRIVILEGES
PROMPT ================================================================================
PROMPT

PROMPT System Privileges:
PROMPT --------------------------------------------------------------------------------
COLUMN grantee FORMAT A30
COLUMN privilege FORMAT A40
COLUMN admin_option FORMAT A12
COLUMN common FORMAT A10

SELECT
   grantee,
   privilege,
   admin_option,
   common
FROM dba_sys_privs
WHERE grantee IN ('C##XSTREAMADMIN', 'C##CONNECTUSER')
ORDER BY grantee, privilege;

PROMPT
PROMPT Role Grants:
PROMPT --------------------------------------------------------------------------------
COLUMN granted_role FORMAT A40

SELECT
   grantee,
   granted_role,
   admin_option,
   common
FROM dba_role_privs
WHERE grantee IN ('C##XSTREAMADMIN', 'C##CONNECTUSER')
ORDER BY grantee, granted_role;

PROMPT
PROMPT Required Privileges Check:
PROMPT --------------------------------------------------------------------------------

DECLARE
   v_count NUMBER;
   TYPE priv_array IS TABLE OF VARCHAR2(100);
   v_xstream_privs priv_array := priv_array(
       'CREATE SESSION', 'SET CONTAINER', 'SELECT ANY DICTIONARY',
       'EXECUTE_CATALOG_ROLE', 'SELECT ANY TRANSACTION'
   );
   v_connect_privs priv_array := priv_array(
       'CREATE SESSION', 'SET CONTAINER', 'SELECT ANY DICTIONARY',
       'SELECT_CATALOG_ROLE'
   );
   v_passed NUMBER := 0;
   v_failed NUMBER := 0;
BEGIN
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('C##XSTREAMADMIN Required Privileges:');
  
   FOR i IN 1..v_xstream_privs.COUNT LOOP
       SELECT COUNT(*) INTO v_count
       FROM dba_sys_privs
       WHERE grantee = 'C##XSTREAMADMIN'
       AND privilege = v_xstream_privs(i);
      
       IF v_count > 0 THEN
           DBMS_OUTPUT.PUT_LINE('  ✓ ' || v_xstream_privs(i));
           v_passed := v_passed + 1;
       ELSE
           DBMS_OUTPUT.PUT_LINE('  ✗ MISSING: ' || v_xstream_privs(i));
           v_failed := v_failed + 1;
       END IF;
   END LOOP;
  
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('C##CONNECTUSER Required Privileges:');
  
   FOR i IN 1..v_connect_privs.COUNT LOOP
       SELECT COUNT(*) INTO v_count
       FROM dba_sys_privs
       WHERE grantee = 'C##CONNECTUSER'
       AND privilege = v_connect_privs(i);
      
       IF v_count > 0 THEN
           DBMS_OUTPUT.PUT_LINE('  ✓ ' || v_connect_privs(i));
           v_passed := v_passed + 1;
       ELSE
           DBMS_OUTPUT.PUT_LINE('  ✗ MISSING: ' || v_connect_privs(i));
           v_failed := v_failed + 1;
       END IF;
   END LOOP;
  
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('Privileges Summary: ' || v_passed || ' found, ' || v_failed || ' missing');
END;
/

PROMPT
PROMPT ================================================================================
PROMPT   SECTION 4: TABLESPACES
PROMPT ================================================================================
PROMPT

PROMPT Tablespaces Check:
PROMPT --------------------------------------------------------------------------------
COLUMN tablespace_name FORMAT A30
COLUMN status FORMAT A10
COLUMN contents FORMAT A15
COLUMN extent_management FORMAT A20
COLUMN bigfile FORMAT A10

SELECT
   tablespace_name,
   status,
   contents,
   extent_management,
   bigfile
FROM dba_tablespaces
WHERE tablespace_name IN ('XSTREAM_ADM_TBS', 'CONNECTUSER_TBS')
ORDER BY tablespace_name;

PROMPT
PROMPT Tablespace Sizes:
PROMPT --------------------------------------------------------------------------------
COLUMN size_mb FORMAT 999,999.99
COLUMN max_size_mb FORMAT 999,999.99
COLUMN autoextensible FORMAT A15

SELECT
   tablespace_name,
   ROUND(SUM(bytes)/1024/1024, 2) as size_mb,
   ROUND(SUM(maxbytes)/1024/1024, 2) as max_size_mb,
   MAX(autoextensible) as autoextensible
FROM dba_data_files
WHERE tablespace_name IN ('XSTREAM_ADM_TBS', 'CONNECTUSER_TBS')
GROUP BY tablespace_name
ORDER BY tablespace_name;

PROMPT
PROMPT User Quotas:
PROMPT --------------------------------------------------------------------------------
COLUMN quota_mb FORMAT A20

SELECT
   username,
   tablespace_name,
   CASE
       WHEN max_bytes = -1 THEN 'UNLIMITED'
       ELSE TO_CHAR(ROUND(max_bytes/1024/1024, 2))
   END as quota_mb
FROM cdb_ts_quotas
WHERE username IN ('C##XSTREAMADMIN', 'C##CONNECTUSER')
ORDER BY username, tablespace_name;

PROMPT
PROMPT Tablespace Status Check:
PROMPT --------------------------------------------------------------------------------

DECLARE
   v_count NUMBER;
   v_passed NUMBER := 0;
   v_failed NUMBER := 0;
BEGIN
   DBMS_OUTPUT.PUT_LINE('');
  
   -- Check XSTREAM_ADM_TBS
   SELECT COUNT(*) INTO v_count
   FROM dba_tablespaces
   WHERE tablespace_name = 'XSTREAM_ADM_TBS'
   AND status = 'ONLINE';
  
   IF v_count > 0 THEN
       DBMS_OUTPUT.PUT_LINE('✓ PASS: XSTREAM_ADM_TBS tablespace exists and is ONLINE');
       v_passed := v_passed + 1;
   ELSE
       DBMS_OUTPUT.PUT_LINE('✗ FAIL: XSTREAM_ADM_TBS tablespace not found or not ONLINE');
       DBMS_OUTPUT.PUT_LINE('        Remediation: CREATE BIGFILE TABLESPACE xstream_adm_tbs DATAFILE SIZE 100M AUTOEXTEND ON;');
       v_failed := v_failed + 1;
   END IF;
  
   -- Check CONNECTUSER_TBS
   SELECT COUNT(*) INTO v_count
   FROM dba_tablespaces
   WHERE tablespace_name = 'CONNECTUSER_TBS'
   AND status = 'ONLINE';
  
   IF v_count > 0 THEN
       DBMS_OUTPUT.PUT_LINE('✓ PASS: CONNECTUSER_TBS tablespace exists and is ONLINE');
       v_passed := v_passed + 1;
   ELSE
       DBMS_OUTPUT.PUT_LINE('✗ FAIL: CONNECTUSER_TBS tablespace not found or not ONLINE');
       DBMS_OUTPUT.PUT_LINE('        Remediation: CREATE BIGFILE TABLESPACE connectuser_tbs DATAFILE SIZE 100M AUTOEXTEND ON;');
       v_failed := v_failed + 1;
   END IF;
  
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('Tablespaces Summary: ' || v_passed || ' passed, ' || v_failed || ' failed');
END;
/

PROMPT
PROMPT ================================================================================
PROMPT   SECTION 5: XSTREAM CONFIGURATION
PROMPT ================================================================================
PROMPT

PROMPT XStream Outbound Servers:
PROMPT --------------------------------------------------------------------------------
COLUMN server_name FORMAT A30
COLUMN connect_user FORMAT A30
COLUMN capture_user FORMAT A30
COLUMN queue_owner FORMAT A30
COLUMN queue_name FORMAT A30
COLUMN status FORMAT A15

SELECT
   server_name,
   connect_user,
   capture_user,
   queue_owner,
   queue_name,
   status
FROM dba_xstream_outbound
ORDER BY server_name;

PROMPT
PROMPT Capture Processes:
PROMPT --------------------------------------------------------------------------------
COLUMN capture_name FORMAT A30
COLUMN queue_name FORMAT A30
COLUMN rule_set_name FORMAT A30
COLUMN start_scn FORMAT 999999999999999

SELECT
   capture_name,
   status,
   queue_name,
   rule_set_name,
   start_scn
FROM dba_capture
ORDER BY capture_name;

PROMPT
PROMPT XStream Status Check:
PROMPT --------------------------------------------------------------------------------

DECLARE
   v_count NUMBER;
   v_status VARCHAR2(50);
   v_server_name VARCHAR2(100);
   v_passed NUMBER := 0;
   v_failed NUMBER := 0;
   v_warnings NUMBER := 0;
BEGIN
   DBMS_OUTPUT.PUT_LINE('');
  
   -- Check XStream Outbound Server
   SELECT COUNT(*) INTO v_count FROM dba_xstream_outbound;
  
   IF v_count > 0 THEN
       SELECT server_name, status INTO v_server_name, v_status
       FROM dba_xstream_outbound WHERE ROWNUM = 1;
      
       IF v_status IN ('ENABLED', 'ATTACHED') THEN
           DBMS_OUTPUT.PUT_LINE('✓ PASS: XStream outbound server ''' || v_server_name || ''' is ' || v_status);
           v_passed := v_passed + 1;
       ELSE
           DBMS_OUTPUT.PUT_LINE('⚠ WARNING: XStream outbound server status is ' || v_status);
           v_warnings := v_warnings + 1;
       END IF;
   ELSE
       DBMS_OUTPUT.PUT_LINE('✗ FAIL: No XStream outbound server configured');
       DBMS_OUTPUT.PUT_LINE('        Remediation: Execute DBMS_XSTREAM_ADM.CREATE_OUTBOUND to create server');
       v_failed := v_failed + 1;
   END IF;
  
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('XStream Summary: ' || v_passed || ' passed, ' || v_failed || ' failed, ' || v_warnings || ' warnings');
END;
/

PROMPT
PROMPT ================================================================================
PROMPT   SECTION 6: CONTAINERS
PROMPT ================================================================================
PROMPT

PROMPT Container List:
PROMPT --------------------------------------------------------------------------------
COLUMN con_id FORMAT 999
COLUMN name FORMAT A30
COLUMN open_mode FORMAT A15
COLUMN restricted FORMAT A15

SELECT
   con_id,
   name,
   open_mode,
   restricted
FROM v$containers
ORDER BY con_id;

PROMPT
PROMPT ================================================================================
PROMPT   FINAL SUMMARY
PROMPT ================================================================================
PROMPT

DECLARE
   -- Counters
   v_db_checks NUMBER := 0;
   v_db_passed NUMBER := 0;
   v_user_checks NUMBER := 0;
   v_user_passed NUMBER := 0;
   v_priv_total NUMBER := 0;
   v_priv_found NUMBER := 0;
   v_tbs_checks NUMBER := 0;
   v_tbs_passed NUMBER := 0;
   v_xstream_ok NUMBER := 0;
  
   -- Temp variables
   v_count NUMBER;
   v_status VARCHAR2(50);
   v_log_mode VARCHAR2(20);
   v_supp_all VARCHAR2(10);
   v_supp_min VARCHAR2(10);
  
   -- Total summary
   v_total_passed NUMBER := 0;
   v_total_failed NUMBER := 0;
   v_total_warnings NUMBER := 0;
BEGIN
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('Overall Configuration Status:');
   DBMS_OUTPUT.PUT_LINE('--------------------------------------------------------------------------------');
  
   -- Database checks
   SELECT log_mode, supplemental_log_data_all, supplemental_log_data_min
   INTO v_log_mode, v_supp_all, v_supp_min
   FROM v$database;
  
   IF v_log_mode = 'ARCHIVELOG' THEN v_db_passed := v_db_passed + 1; END IF;
   IF v_supp_all = 'YES' OR v_supp_min = 'YES' THEN v_db_passed := v_db_passed + 1; END IF;
   v_db_checks := 2;
  
   -- User checks
   SELECT COUNT(*) INTO v_count
   FROM cdb_users
   WHERE username IN ('C##XSTREAMADMIN', 'C##CONNECTUSER')
   AND account_status = 'OPEN';
   v_user_passed := v_count;
   v_user_checks := 2;
  
   -- Privilege checks (simplified)
   SELECT COUNT(*) INTO v_priv_found
   FROM dba_sys_privs
   WHERE grantee IN ('C##XSTREAMADMIN', 'C##CONNECTUSER');
   v_priv_total := 9; -- Expected minimum privileges
  
   -- Tablespace checks
   SELECT COUNT(*) INTO v_count
   FROM dba_tablespaces
   WHERE tablespace_name IN ('XSTREAM_ADM_TBS', 'CONNECTUSER_TBS')
   AND status = 'ONLINE';
   v_tbs_passed := v_count;
   v_tbs_checks := 2;
  
   -- XStream check
   SELECT COUNT(*) INTO v_xstream_ok
   FROM dba_xstream_outbound
   WHERE status IN ('ENABLED', 'ATTACHED');
  
   -- Calculate totals
   v_total_passed := v_db_passed + v_user_passed + v_tbs_passed + v_xstream_ok;
   v_total_failed := (v_db_checks - v_db_passed) + (v_user_checks - v_user_passed) +
                    (v_tbs_checks - v_tbs_passed) + (1 - v_xstream_ok);
  
   IF v_priv_found < v_priv_total THEN
       v_total_warnings := v_priv_total - v_priv_found;
   END IF;
  
   -- Display summary
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('  Database Configuration:  ' || v_db_passed || '/' || v_db_checks || ' checks passed');
   DBMS_OUTPUT.PUT_LINE('  User Accounts:           ' || v_user_passed || '/' || v_user_checks || ' users configured');
   DBMS_OUTPUT.PUT_LINE('  Privileges:              ' || v_priv_found || ' privileges granted');
   DBMS_OUTPUT.PUT_LINE('  Tablespaces:             ' || v_tbs_passed || '/' || v_tbs_checks || ' tablespaces online');
   DBMS_OUTPUT.PUT_LINE('  XStream:                 ' || v_xstream_ok || ' outbound server(s) active');
   DBMS_OUTPUT.PUT_LINE('');
   DBMS_OUTPUT.PUT_LINE('  Total Passed:            ' || v_total_passed);
   DBMS_OUTPUT.PUT_LINE('  Total Failed:            ' || v_total_failed);
   DBMS_OUTPUT.PUT_LINE('  Total Warnings:          ' || v_total_warnings);
   DBMS_OUTPUT.PUT_LINE('');
  
   IF v_total_failed = 0 AND v_total_warnings = 0 THEN
       DBMS_OUTPUT.PUT_LINE('  ✓✓✓ OVERALL STATUS: PASS - Configuration is correct ✓✓✓');
   ELSIF v_total_failed = 0 THEN
       DBMS_OUTPUT.PUT_LINE('  ⚠⚠⚠ OVERALL STATUS: PASS WITH WARNINGS ⚠⚠⚠');
   ELSE
       DBMS_OUTPUT.PUT_LINE('  ✗✗✗ OVERALL STATUS: FAIL - ' || v_total_failed || ' critical issue(s) found ✗✗✗');
   END IF;
  
   DBMS_OUTPUT.PUT_LINE('');
END;
/

PROMPT
PROMPT ================================================================================
PROMPT   Verification Complete
PROMPT   Review the results above and apply any recommended remediations.
PROMPT ================================================================================
PROMPT
PROMPT For detailed remediation steps, see:
PROMPT   - Snowflake Documentation: Configure Oracle database for Openflow Connector
PROMPT   - Oracle Documentation: XStream Administrator's Guide
PROMPT
PROMPT Script execution completed at:
SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI:SS') as "Timestamp" FROM dual;
PROMPT
PROMPT ================================================================================

-- Reset settings
SET ECHO ON
SET FEEDBACK ON
SET VERIFY ON

"""
Oracle Openflow Connector Configuration Verifier
SNOWFLAKE STREAMLIT VERSION - Upload this file to Snowflake
"""

import streamlit as st
import pandas as pd
from typing import Dict
import json
from oracle_connection_snowflake import OracleConnectionSnowflake, create_connection_ui_snowflake

# Page configuration
st.set_page_config(
    page_title="Oracle Openflow Connector Verifier",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #29B5E8;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #29B5E8;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #29B5E8;
        padding-bottom: 0.5rem;
    }
    .status-pass {
        background-color: #d4edda;
        color: #155724;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    .status-fail {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #dc3545;
        margin: 0.5rem 0;
    }
    .status-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
        margin: 0.5rem 0;
    }
    .info-box {
        background-color: #e7f3ff;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">🔍 Oracle Openflow Connector Configuration Verifier</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align: center; color: #666;">🏔️ Running in Snowflake Streamlit</div>', unsafe_allow_html=True)

# Sidebar - Connection Management
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Create connection UI
    oracle_conn = create_connection_ui_snowflake()
    
    st.markdown("---")
    st.markdown("### Check Options")
    check_all = st.checkbox("Run All Checks", value=True)
    
    if not check_all:
        check_database = st.checkbox("Database Config", value=True)
        check_users = st.checkbox("Users", value=True)
        check_privileges = st.checkbox("Privileges", value=True)
        check_xstream = st.checkbox("XStream", value=True)
        check_tablespaces = st.checkbox("Tablespaces", value=True)
    
    st.markdown("---")
    run_check = st.button("🚀 Run Verification", type="primary", use_container_width=True)

# Main content tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "👥 Users & Privileges",
    "🗄️ XStream Configuration",
    "📋 Detailed Report",
    "💡 Remediation Guide"
])

def generate_verification_sql() -> Dict[str, str]:
    """Generate SQL queries for verification - Run in CDB$ROOT context"""
    return {
        "set_container": """
            ALTER SESSION SET CONTAINER = CDB$ROOT
        """,
        "database_info": """
            SELECT 
                d.name as database_name,
                d.cdb,
                d.log_mode,
                d.force_logging,
                d.supplemental_log_data_min,
                d.supplemental_log_data_all,
                (SELECT banner FROM v$version WHERE banner LIKE 'Oracle%') as version
            FROM v$database d
        """,
        "users_check": """
            SELECT 
                username,
                account_status,
                common,
                default_tablespace,
                created,
                oracle_maintained
            FROM dba_users
            WHERE username IN ('C##XSTREAMADMIN', 'C##CONNECTUSER')
            ORDER BY username
        """,
        "user_privileges": """
            SELECT 
                grantee,
                privilege,
                admin_option,
                common,
                inherited
            FROM dba_sys_privs
            WHERE grantee IN ('C##XSTREAMADMIN', 'C##CONNECTUSER')
            ORDER BY grantee, privilege
        """,
        "user_roles": """
            SELECT 
                grantee,
                granted_role,
                admin_option,
                common,
                inherited
            FROM dba_role_privs
            WHERE grantee IN ('C##XSTREAMADMIN', 'C##CONNECTUSER')
            ORDER BY grantee, granted_role
        """,
        "tablespaces": """
            SELECT 
                tablespace_name,
                status,
                contents,
                extent_management,
                segment_space_management,
                bigfile
            FROM dba_tablespaces
            WHERE tablespace_name IN ('XSTREAM_ADM_TBS', 'CONNECTUSER_TBS')
        """,
        "tablespace_size": """
            SELECT 
                tablespace_name,
                ROUND(SUM(bytes)/1024/1024, 2) as size_mb,
                ROUND(SUM(maxbytes)/1024/1024, 2) as max_size_mb,
                MAX(autoextensible) as autoextensible
            FROM dba_data_files
            WHERE tablespace_name IN ('XSTREAM_ADM_TBS', 'CONNECTUSER_TBS')
            GROUP BY tablespace_name
        """,
        "user_quotas": """
            SELECT 
                username,
                tablespace_name,
                CASE 
                    WHEN max_bytes = -1 THEN 'UNLIMITED'
                    ELSE TO_CHAR(ROUND(max_bytes/1024/1024, 2))
                END as quota_mb
            FROM dba_ts_quotas
            WHERE username IN ('C##XSTREAMADMIN', 'C##CONNECTUSER')
        """,
        "xstream_outbound": """
            SELECT 
                server_name,
                connect_user,
                capture_user,
                queue_owner,
                queue_name,
                status
            FROM dba_xstream_outbound
        """,
        "xstream_capture": """
            SELECT 
                capture_name,
                status,
                queue_name,
                rule_set_name,
                start_scn,
                captured_scn,
                applied_scn,
                required_checkpoint_scn
            FROM dba_capture
        """,
        "xstream_capture_stats": """
            SELECT 
                capture_name,
                state,
                total_messages_captured,
                total_messages_enqueued
            FROM v$xstream_capture
        """,
        "queues": """
            SELECT 
                name,
                queue_table,
                queue_type,
                enqueue_enabled,
                dequeue_enabled,
                retention,
                user_comment
            FROM dba_queues
            WHERE queue_table LIKE '%XOUT%' OR name LIKE '%XOUT%'
        """,
        "containers": """
            SELECT 
                con_id,
                name,
                open_mode,
                restricted
            FROM v$containers
            ORDER BY con_id
        """,
        "current_container": """
            SELECT 
                SYS_CONTEXT('USERENV', 'CON_NAME') as container_name,
                SYS_CONTEXT('USERENV', 'CON_ID') as container_id,
                SYS_CONTEXT('USERENV', 'CURRENT_USER') as current_user,
                SYS_CONTEXT('USERENV', 'SESSION_USER') as session_user
            FROM dual
        """
    }

def analyze_configuration(results: Dict) -> Dict:
    """Analyze configuration and generate findings"""
    findings = {
        "summary": {
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0
        },
        "details": []
    }
    
    # Check 1: Database Configuration
    if "database_info" in results and not results["database_info"].empty:
        db_info = results["database_info"].iloc[0]
        
        # Archive Log Mode
        findings["summary"]["total_checks"] += 1
        if db_info.get("LOG_MODE") == "ARCHIVELOG":
            findings["summary"]["passed"] += 1
            findings["details"].append({
                "category": "Database",
                "check": "Archive Log Mode",
                "status": "PASS",
                "message": "Database is in ARCHIVELOG mode",
                "value": db_info.get("LOG_MODE")
            })
        else:
            findings["summary"]["failed"] += 1
            findings["details"].append({
                "category": "Database",
                "check": "Archive Log Mode",
                "status": "FAIL",
                "message": "Database must be in ARCHIVELOG mode for CDC",
                "value": db_info.get("LOG_MODE"),
                "remediation": "Execute: ALTER DATABASE ARCHIVELOG;"
            })
        
        # Supplemental Logging
        findings["summary"]["total_checks"] += 1
        supp_log_min = db_info.get("SUPPLEMENTAL_LOG_DATA_MIN", "NO")
        supp_log_all = db_info.get("SUPPLEMENTAL_LOG_DATA_ALL", "NO")
        
        if supp_log_all == "YES":
            # ALL COLUMNS logging includes minimal logging
            findings["summary"]["passed"] += 1
            findings["details"].append({
                "category": "Database",
                "check": "Supplemental Logging",
                "status": "PASS",
                "message": "Full supplemental logging (ALL COLUMNS) is enabled",
                "value": f"MIN: {supp_log_min}, ALL: {supp_log_all}"
            })
        elif supp_log_min == "YES":
            # Minimal is set but not ALL COLUMNS - recommend upgrading
            findings["summary"]["passed"] += 1
            findings["details"].append({
                "category": "Database",
                "check": "Supplemental Logging",
                "status": "PASS",
                "message": "Minimal supplemental logging is enabled (consider upgrading to ALL COLUMNS)",
                "value": f"MIN: {supp_log_min}, ALL: {supp_log_all}",
                "remediation": "Recommended: ALTER DATABASE ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;"
            })
        else:
            findings["summary"]["failed"] += 1
            findings["details"].append({
                "category": "Database",
                "check": "Supplemental Logging",
                "status": "FAIL",
                "message": "Supplemental logging must be enabled",
                "value": f"MIN: {supp_log_min}, ALL: {supp_log_all}",
                "remediation": "ALTER SESSION SET CONTAINER = CDB$ROOT;\nALTER DATABASE ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;"
            })
        
        # CDB Check
        findings["summary"]["total_checks"] += 1
        if db_info.get("CDB") == "YES":
            findings["summary"]["passed"] += 1
            findings["details"].append({
                "category": "Database",
                "check": "Container Database",
                "status": "PASS",
                "message": "Database is a Container Database (CDB)",
                "value": db_info.get("CDB")
            })
        else:
            findings["summary"]["warnings"] += 1
            findings["details"].append({
                "category": "Database",
                "check": "Container Database",
                "status": "WARNING",
                "message": "Database is not a CDB. Ensure proper configuration for non-CDB",
                "value": db_info.get("CDB")
            })
    
    # Check 2: Users (in CDB$ROOT context)
    if "users_check" in results and not results["users_check"].empty:
        users_df = results["users_check"]
        
        for required_user in ["C##XSTREAMADMIN", "C##CONNECTUSER"]:
            findings["summary"]["total_checks"] += 1
            user_rows = users_df[users_df["USERNAME"] == required_user]
            
            if not user_rows.empty:
                user_info = user_rows.iloc[0]
                if user_info["ACCOUNT_STATUS"] == "OPEN":
                    # Check if it's a common user
                    is_common = user_info.get("COMMON", "NO") == "YES"
                    findings["summary"]["passed"] += 1
                    findings["details"].append({
                        "category": "Users",
                        "check": f"User {required_user}",
                        "status": "PASS",
                        "message": f"User {required_user} exists and is OPEN",
                        "value": f"Status: {user_info['ACCOUNT_STATUS']}, Common: {is_common}, Tablespace: {user_info.get('DEFAULT_TABLESPACE', 'N/A')}"
                    })
                else:
                    findings["summary"]["failed"] += 1
                    findings["details"].append({
                        "category": "Users",
                        "check": f"User {required_user}",
                        "status": "FAIL",
                        "message": f"User {required_user} is {user_info['ACCOUNT_STATUS']} (should be OPEN)",
                        "value": f"Status: {user_info['ACCOUNT_STATUS']}",
                        "remediation": f"ALTER USER {required_user} ACCOUNT UNLOCK;"
                    })
            else:
                findings["summary"]["failed"] += 1
                findings["details"].append({
                    "category": "Users",
                    "check": f"User {required_user}",
                    "status": "FAIL",
                    "message": f"User {required_user} does not exist in CDB$ROOT",
                    "remediation": f"ALTER SESSION SET CONTAINER = CDB$ROOT;\nCREATE USER {required_user} IDENTIFIED BY password CONTAINER=ALL;"
                })
    
    # Check 3: XStream Outbound Server
    if "xstream_outbound" in results:
        findings["summary"]["total_checks"] += 1
        if not results["xstream_outbound"].empty:
            xstream = results["xstream_outbound"].iloc[0]
            if xstream.get("STATUS") in ["ENABLED", "ATTACHED"]:
                findings["summary"]["passed"] += 1
                findings["details"].append({
                    "category": "XStream",
                    "check": "Outbound Server",
                    "status": "PASS",
                    "message": f"XStream outbound server '{xstream.get('SERVER_NAME')}' is {xstream.get('STATUS')}",
                    "value": f"Connect User: {xstream.get('CONNECT_USER')}, Queue: {xstream.get('QUEUE_NAME', 'N/A')}"
                })
            else:
                findings["summary"]["warnings"] += 1
                findings["details"].append({
                    "category": "XStream",
                    "check": "Outbound Server",
                    "status": "WARNING",
                    "message": f"XStream outbound server status is {xstream.get('STATUS')}",
                    "value": f"Server: {xstream.get('SERVER_NAME')}"
                })
        else:
            findings["summary"]["failed"] += 1
            findings["details"].append({
                "category": "XStream",
                "check": "Outbound Server",
                "status": "FAIL",
                "message": "No XStream outbound server configured",
                "remediation": "Execute DBMS_XSTREAM_ADM.CREATE_OUTBOUND to create server"
            })
    
    return findings

def create_status_box(status: str, message: str) -> str:
    """Create a colored status box"""
    if status == "PASS":
        return f'<div class="status-pass">✅ {message}</div>'
    elif status == "FAIL":
        return f'<div class="status-fail">❌ {message}</div>'
    else:
        return f'<div class="status-warning">⚠️ {message}</div>'

# Tab 1: Dashboard
with tab1:
    st.markdown('<div class="section-header">Configuration Overview</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>ℹ️ About this Tool</strong><br>
        This application verifies that your Oracle database is properly configured for the Snowflake Openflow Connector.
        <br><br>
        <strong>🏔️ Running in Snowflake Streamlit</strong> with External Access Integration
    </div>
    """, unsafe_allow_html=True)
    
    if run_check and oracle_conn and oracle_conn.is_connected():
        with st.spinner("Running verification checks..."):
            try:
                # Generate queries
                queries = generate_verification_sql()
                
                # Set container to CDB$ROOT first
                try:
                    oracle_conn.execute_ddl("ALTER SESSION SET CONTAINER = CDB$ROOT")
                    st.info("🏛️ Session set to CDB$ROOT container")
                except Exception as e:
                    st.warning(f"⚠️ Could not set container to CDB$ROOT: {str(e)}")
                    st.info("ℹ️ Continuing with default container...")
                
                # Remove set_container from queries dict (already executed)
                if "set_container" in queries:
                    del queries["set_container"]
                
                # Execute verification queries
                results = oracle_conn.execute_queries(queries)
                
                # Analyze results
                findings = analyze_configuration(results)
                
                # Store in session state
                st.session_state['results'] = results
                st.session_state['findings'] = findings
                
                # Display container context
                if "current_container" in results and not results["current_container"].empty:
                    container_info = results["current_container"].iloc[0]
                    st.success(f"📍 Running in Container: **{container_info.get('CONTAINER_NAME', 'Unknown')}** (ID: {container_info.get('CONTAINER_ID', 'N/A')})")
                
                # Display summary metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Checks", findings["summary"]["total_checks"])
                with col2:
                    st.metric("✅ Passed", findings["summary"]["passed"])
                with col3:
                    st.metric("❌ Failed", findings["summary"]["failed"])
                with col4:
                    st.metric("⚠️ Warnings", findings["summary"]["warnings"])
                
                # Overall Status
                st.markdown("### Overall Status")
                if findings["summary"]["failed"] == 0:
                    if findings["summary"]["warnings"] == 0:
                        st.success("✅ **PASS** - Oracle database is correctly configured")
                    else:
                        st.warning(f"⚠️ **PASS WITH WARNINGS** - {findings['summary']['warnings']} warning(s)")
                else:
                    st.error(f"❌ **FAIL** - {findings['summary']['failed']} critical issue(s)")
                
                # Status by Category
                st.markdown("### Status by Category")
                categories = {}
                for detail in findings["details"]:
                    cat = detail["category"]
                    if cat not in categories:
                        categories[cat] = {"PASS": 0, "FAIL": 0, "WARNING": 0}
                    categories[cat][detail["status"]] += 1
                
                for cat, stats in categories.items():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.markdown(f"**{cat}**")
                    with col2:
                        if stats["FAIL"] > 0:
                            st.error(f"❌ {stats['FAIL']} Failed, ⚠️ {stats['WARNING']} Warnings, ✅ {stats['PASS']} Passed")
                        elif stats["WARNING"] > 0:
                            st.warning(f"⚠️ {stats['WARNING']} Warnings, ✅ {stats['PASS']} Passed")
                        else:
                            st.success(f"✅ All {stats['PASS']} checks passed")
            
            except Exception as e:
                st.error(f"❌ Error running verification: {str(e)}")
                st.exception(e)
    
    elif run_check and not oracle_conn:
        st.warning("⚠️ Please connect to Oracle database first using the sidebar")
    
    else:
        st.info("👈 Connect to Oracle using the sidebar and click 'Run Verification' to start")

# Tab 2: Users & Privileges  
with tab2:
    st.markdown('<div class="section-header">Users & Privileges Analysis</div>', unsafe_allow_html=True)
    
    if st.session_state.get('results'):
        results = st.session_state['results']
        
        st.markdown("### Configured Users")
        if "users_check" in results and not results["users_check"].empty:
            st.dataframe(results["users_check"], use_container_width=True)
        else:
            st.info("No user data available")
        
        st.markdown("### User Privileges")
        if "user_privileges" in results and not results["user_privileges"].empty:
            st.dataframe(results["user_privileges"], use_container_width=True)
        else:
            st.info("No privilege data available")
        
        st.markdown("### User Roles")
        if "user_roles" in results and not results["user_roles"].empty:
            st.dataframe(results["user_roles"], use_container_width=True)
        else:
            st.info("No role data available")
    else:
        st.info("Run verification to see user and privilege information")

# Tab 3: XStream Configuration
with tab3:
    st.markdown('<div class="section-header">XStream Configuration Details</div>', unsafe_allow_html=True)
    
    if st.session_state.get('results'):
        results = st.session_state['results']
        
        st.markdown("### XStream Outbound Server")
        if "xstream_outbound" in results and not results["xstream_outbound"].empty:
            st.dataframe(results["xstream_outbound"], use_container_width=True)
        else:
            st.warning("⚠️ No XStream outbound server found")
        
        st.markdown("### Capture Process")
        if "xstream_capture" in results and not results["xstream_capture"].empty:
            st.dataframe(results["xstream_capture"], use_container_width=True)
        else:
            st.warning("⚠️ No capture process found")
        
        st.markdown("### Queues")
        if "queues" in results and not results["queues"].empty:
            st.dataframe(results["queues"], use_container_width=True)
        else:
            st.info("No queue data available")
    else:
        st.info("Run verification to see XStream configuration")

# Tab 4: Detailed Report
with tab4:
    st.markdown('<div class="section-header">Detailed Verification Report</div>', unsafe_allow_html=True)
    
    if st.session_state.get('findings'):
        findings = st.session_state['findings']
        
        # Export options
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📄 Export JSON"):
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(findings, indent=2),
                    file_name="oracle_config_verification.json",
                    mime="application/json"
                )
        
        # Detailed findings
        st.markdown("### All Checks")
        
        categories = {}
        for detail in findings["details"]:
            cat = detail["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(detail)
        
        for cat, checks in categories.items():
            with st.expander(f"**{cat}** ({len(checks)} checks)", expanded=True):
                for check in checks:
                    status_html = create_status_box(check["status"], check["message"])
                    st.markdown(status_html, unsafe_allow_html=True)
                    
                    if check.get("value"):
                        st.markdown(f"**Value:** `{check['value']}`")
                    
                    if check.get("remediation"):
                        st.code(check["remediation"], language="sql")
                    
                    st.markdown("---")
    else:
        st.info("Run verification to see detailed report")

# Tab 5: Remediation Guide  
with tab5:
    st.markdown('<div class="section-header">Remediation Guide</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### Common Remediation Steps
    
    Use these SQL scripts to fix common issues found during verification.
    """)
    
    with st.expander("Enable Archive Log Mode", expanded=False):
        st.code("""
-- Enable archive log mode (requires database restart)
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
ALTER DATABASE ARCHIVELOG;
ALTER DATABASE OPEN;
        """, language="sql")
    
    with st.expander("Enable Supplemental Logging", expanded=False):
        st.code("""
-- Enable full supplemental logging (ALL COLUMNS) - Recommended by Snowflake
ALTER SESSION SET CONTAINER = CDB$ROOT;
ALTER DATABASE ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;

-- Verify
SELECT 
    supplemental_log_data_min,
    supplemental_log_data_all
FROM v$database;
-- Expected: SUPPLEMENTAL_LOG_DATA_ALL = YES
        """, language="sql")
    
    with st.expander("Create Common Users", expanded=False):
        st.code("""
-- Create C##XSTREAMADMIN user
CREATE USER c##xstreamadmin IDENTIFIED BY "YourPassword123"
  DEFAULT TABLESPACE xstream_adm_tbs
  QUOTA UNLIMITED ON xstream_adm_tbs
  CONTAINER = ALL;

-- Create C##CONNECTUSER
CREATE USER c##connectuser IDENTIFIED BY "YourPassword456"
  DEFAULT TABLESPACE connectuser_tbs
  QUOTA UNLIMITED ON connectuser_tbs
  CONTAINER = ALL;
        """, language="sql")
    
    with st.expander("Grant Required Privileges", expanded=False):
        st.code("""
-- Grants for C##XSTREAMADMIN
GRANT CREATE SESSION TO c##xstreamadmin CONTAINER=ALL;
GRANT SET CONTAINER TO c##xstreamadmin CONTAINER=ALL;
GRANT SELECT ANY DICTIONARY TO c##xstreamadmin CONTAINER=ALL;
GRANT EXECUTE_CATALOG_ROLE TO c##xstreamadmin CONTAINER=ALL;

-- Grants for C##CONNECTUSER
GRANT CREATE SESSION TO c##connectuser CONTAINER=ALL;
GRANT SET CONTAINER TO c##connectuser CONTAINER=ALL;
GRANT SELECT ANY TABLE TO c##connectuser CONTAINER=ALL;
GRANT SELECT_CATALOG_ROLE TO c##connectuser CONTAINER=ALL;
        """, language="sql")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>🏔️ Oracle Openflow Connector Configuration Verifier | Snowflake Streamlit Edition</p>
    <p>External Access Integration: oracle_external_access_integration</p>
</div>
""", unsafe_allow_html=True)


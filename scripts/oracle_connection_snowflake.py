"""
Oracle Database Connection Helper for Snowflake Streamlit
Works with Snowflake External Access Integration and Secrets
"""

import oracledb
import pandas as pd
import json
import os
from typing import Dict, Optional, Tuple
import streamlit as st

class OracleConnectionSnowflake:
    """Manages Oracle database connections in Snowflake Streamlit"""
    
    def __init__(self, config_file: str = "oracle_config.json"):
        """
        Initialize Oracle connection manager for Snowflake
        
        Args:
            config_file: Path to JSON configuration file
        """
        self.config_file = config_file
        self.connection = None
        self.config = self._load_config()
        self.is_snowflake_env = self._detect_snowflake_environment()
    
    def _detect_snowflake_environment(self) -> bool:
        """Detect if running in Snowflake Streamlit environment"""
        # Snowflake Streamlit has specific session state attributes
        return hasattr(st, 'session_state') and '_snowflake' in dir(st.session_state)
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {"connections": {}, "default_connection": None}
    
    def _get_secret_password(self, secret_name: str) -> Optional[str]:
        """
        Get password from Snowflake secret
        
        Args:
            secret_name: Name of the Snowflake secret
            
        Returns:
            Password string or None
        """
        if not self.is_snowflake_env:
            return None
        
        try:
            # Access Snowflake secrets through session
            secrets = st.secrets.get("secrets", {})
            return secrets.get(secret_name)
        except Exception as e:
            st.warning(f"Could not access secret '{secret_name}': {e}")
            return None
    
    def _get_snowflake_connection_string(self) -> Optional[str]:
        """Get Snowflake connection string if configured"""
        try:
            if hasattr(st, 'connection'):
                # Try to get Snowflake connection for Oracle
                return st.connection('oracle', type='sql')
        except:
            return None
    
    def get_connection_names(self) -> list:
        """Get list of available connection names"""
        return [name for name, conn in self.config.get("connections", {}).items() 
                if conn.get("enabled", True)]
    
    def get_connection_info(self, connection_name: str) -> Optional[Dict]:
        """Get connection information"""
        return self.config.get("connections", {}).get(connection_name)
    
    def connect(self, connection_name: str = None, 
                hostname: str = None, 
                port: int = None,
                service_name: str = None,
                username: str = None,
                password: str = None,
                use_secret: bool = True) -> Tuple[bool, str]:
        """
        Connect to Oracle database
        
        Args:
            connection_name: Name from config file
            hostname: Oracle host (if not using config)
            port: Oracle port
            service_name: Oracle service name
            username: Oracle username
            password: Oracle password (or will use Snowflake secret)
            use_secret: Try to use Snowflake secret for password
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Get connection details from config or parameters
            if connection_name:
                conn_info = self.get_connection_info(connection_name)
                if not conn_info:
                    return False, f"Connection '{connection_name}' not found in config"
                
                hostname = conn_info.get("hostname")
                port = conn_info.get("port", 1521)
                service_name = conn_info.get("service_name")
                username = conn_info.get("username")
                
                # Try to get password from Snowflake secret first
                if use_secret and self.is_snowflake_env and not password:
                    secret_name = conn_info.get("secret_name")
                    if secret_name:
                        password = self._get_secret_password(secret_name)
                
                # Fall back to config password
                if not password:
                    password = conn_info.get("password")
            
            if not all([hostname, port, service_name, username]):
                return False, "Missing required connection parameters (hostname, port, service_name, username)"
            
            if not password:
                return False, "Password not provided and no Snowflake secret configured"
            
            # Create DSN
            dsn = oracledb.makedsn(hostname, port, service_name=service_name)
            
            # Connect
            self.connection = oracledb.connect(
                user=username,
                password=password,
                dsn=dsn
            )
            
            # Test connection
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            cursor.close()
            
            env_info = "Snowflake Streamlit" if self.is_snowflake_env else "Local"
            return True, f"Connected to {hostname}:{port}/{service_name} (via {env_info})"
            
        except oracledb.DatabaseError as e:
            error_obj, = e.args
            return False, f"Oracle Error: {error_obj.message}"
        except Exception as e:
            return False, f"Connection Error: {str(e)}"
    
    def disconnect(self):
        """Disconnect from Oracle"""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                return True, "Disconnected successfully"
            except Exception as e:
                return False, f"Disconnect Error: {str(e)}"
        return True, "Not connected"
    
    def is_connected(self) -> bool:
        """Check if connected to Oracle"""
        if not self.connection:
            return False
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            cursor.close()
            return True
        except:
            return False
    
    def execute_ddl(self, sql: str):
        """
        Execute DDL statement (ALTER, CREATE, DROP, etc.) that doesn't return rows
        
        Args:
            sql: DDL statement to execute
            
        Returns:
            True if successful
        """
        if not self.is_connected():
            raise Exception("Not connected to Oracle database")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            cursor.close()
            return True
            
        except oracledb.DatabaseError as e:
            error_obj, = e.args
            raise Exception(f"DDL Error: {error_obj.message}")
    
    def execute_query(self, sql: str, return_df: bool = True):
        """
        Execute SQL query
        
        Args:
            sql: SQL query to execute
            return_df: Return results as pandas DataFrame
            
        Returns:
            DataFrame if return_df=True, else list of rows
        """
        if not self.is_connected():
            raise Exception("Not connected to Oracle database")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch results
            rows = cursor.fetchall()
            cursor.close()
            
            if return_df and columns:
                return pd.DataFrame(rows, columns=columns)
            return rows
            
        except oracledb.DatabaseError as e:
            error_obj, = e.args
            raise Exception(f"Query Error: {error_obj.message}")
    
    def execute_queries(self, queries: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        """
        Execute multiple queries
        
        Args:
            queries: Dictionary of {query_name: sql_query}
            
        Returns:
            Dictionary of {query_name: DataFrame}
        """
        results = {}
        for name, sql in queries.items():
            try:
                results[name] = self.execute_query(sql, return_df=True)
            except Exception as e:
                st.warning(f"Query '{name}' failed: {str(e)}")
                results[name] = pd.DataFrame()  # Empty DataFrame on error
        return results
    
    def test_connection(self, connection_name: str = None, **kwargs) -> Tuple[bool, str, Dict]:
        """
        Test Oracle connection and get basic info
        
        Returns:
            Tuple of (success, message, info_dict)
        """
        success, msg = self.connect(connection_name, **kwargs)
        if not success:
            return False, msg, {}
        
        try:
            # Get database info (compatible with Oracle 19c, 21c, 23c)
            info_query = """
                SELECT 
                    d.name as database_name,
                    d.cdb,
                    d.log_mode,
                    d.force_logging,
                    d.supplemental_log_data_min,
                    (SELECT banner FROM v$version WHERE banner LIKE 'Oracle%') as version
                FROM v$database d
            """
            df = self.execute_query(info_query)
            info = df.to_dict('records')[0] if not df.empty else {}
            
            return True, "Connection successful", info
            
        except Exception as e:
            return True, f"Connected but info query failed: {str(e)}", {}


def create_connection_ui_snowflake():
    """
    Create Streamlit UI for Oracle connection management in Snowflake
    Returns configured OracleConnectionSnowflake object
    """
    st.sidebar.markdown("### 🔌 Oracle Connection")
    
    # Initialize connection manager
    oracle_conn = OracleConnectionSnowflake()
    
    # Show environment info
    if oracle_conn.is_snowflake_env:
        st.sidebar.info("🏔️ Running in Snowflake Streamlit")
        st.sidebar.caption("Using External Access Integration")
    else:
        st.sidebar.info("💻 Running Locally")
        st.sidebar.caption("Direct Oracle connection")
    
    # Connection mode
    conn_mode = st.sidebar.radio(
        "Connection Mode",
        ["Saved Connection", "Manual Entry"],
        help="Choose how to connect to Oracle"
    )
    
    if conn_mode == "Saved Connection":
        connection_names = oracle_conn.get_connection_names()
        
        if not connection_names:
            st.sidebar.warning("⚠️ No connections configured. Use Manual Entry.")
            return None
        
        selected_conn = st.sidebar.selectbox(
            "Select Connection",
            connection_names,
            help="Choose from saved connections"
        )
        
        conn_info = oracle_conn.get_connection_info(selected_conn)
        if conn_info:
            st.sidebar.text(f"📍 {conn_info.get('description', '')}")
            st.sidebar.text(f"🖥️ {conn_info.get('hostname')}:{conn_info.get('port')}")
            st.sidebar.text(f"👤 {conn_info.get('username')}")
            
            # Check if secret is configured
            secret_name = conn_info.get('secret_name')
            if secret_name and oracle_conn.is_snowflake_env:
                st.sidebar.success(f"🔐 Using Snowflake secret")
                password = None  # Will use secret
                use_secret = True
            else:
                st.sidebar.warning("⚠️ No secret configured")
                password = st.sidebar.text_input(
                    "Password",
                    type="password",
                    key="saved_password",
                    help="Enter password (secret not configured)"
                )
                use_secret = False
        else:
            password = None
            use_secret = False
        
        if st.sidebar.button("🔌 Connect", key="connect_saved"):
            with st.spinner("Connecting to Oracle..."):
                success, message, info = oracle_conn.test_connection(
                    selected_conn,
                    password=password,
                    use_secret=use_secret
                )
                if success:
                    st.sidebar.success(f"✅ {message}")
                    if info:
                        with st.sidebar.expander("Database Info"):
                            st.json(info)
                    st.session_state['oracle_conn'] = oracle_conn
                    st.session_state['connected'] = True
                    st.rerun()
                else:
                    st.sidebar.error(f"❌ {message}")
                    
                    # Show troubleshooting for Snowflake environment
                    if oracle_conn.is_snowflake_env and "No route to host" in message:
                        st.sidebar.error("""
                        🔧 External Access Integration Required!
                        
                        Run this SQL in Snowflake:
                        ```sql
                        -- See snowflake_external_access_setup.sql
                        CREATE NETWORK RULE oracle_network_rule
                          MODE = EGRESS
                          TYPE = HOST_PORT
                          VALUE_LIST = ('3.148.210.65:1521');
                          
                        CREATE EXTERNAL ACCESS INTEGRATION ...
                        ```
                        """)
                    return None
    
    else:  # Manual Entry
        st.sidebar.markdown("---")
        hostname = st.sidebar.text_input(
            "Hostname",
            value="3.148.210.65",
            help="Oracle server hostname or IP"
        )
        port = st.sidebar.number_input(
            "Port",
            value=1521,
            min_value=1,
            max_value=65535
        )
        service_name = st.sidebar.text_input(
            "Service Name",
            value="FREEPDB1",
            help="Oracle service name (e.g., FREEPDB1)"
        )
        username = st.sidebar.text_input(
            "Username",
            value="system",
            help="Oracle username"
        )
        password = st.sidebar.text_input(
            "Password",
            type="password",
            key="manual_password",
            help="Password (or leave blank to use Snowflake secret)"
        )
        
        if st.sidebar.button("🔌 Connect", key="connect_manual"):
            with st.spinner("Connecting to Oracle..."):
                success, message, info = oracle_conn.test_connection(
                    hostname=hostname,
                    port=port,
                    service_name=service_name,
                    username=username,
                    password=password,
                    use_secret=not bool(password)
                )
                if success:
                    st.sidebar.success(f"✅ {message}")
                    if info:
                        with st.sidebar.expander("Database Info"):
                            st.json(info)
                    st.session_state['oracle_conn'] = oracle_conn
                    st.session_state['connected'] = True
                    st.rerun()
                else:
                    st.sidebar.error(f"❌ {message}")
                    return None
    
    # Check if already connected
    if 'oracle_conn' in st.session_state and st.session_state.get('connected'):
        oracle_conn = st.session_state['oracle_conn']
        if oracle_conn.is_connected():
            st.sidebar.success("✅ Connected to Oracle")
            
            # Show connection details
            with st.sidebar.expander("Connection Details", expanded=False):
                st.text(f"Environment: {'Snowflake' if oracle_conn.is_snowflake_env else 'Local'}")
                st.text(f"Status: Connected")
            
            if st.sidebar.button("🔌 Disconnect"):
                oracle_conn.disconnect()
                st.session_state['connected'] = False
                st.rerun()
            return oracle_conn
    
    return None


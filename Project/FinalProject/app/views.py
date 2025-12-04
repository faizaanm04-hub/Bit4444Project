# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Flask modules
from flask   import render_template, request, redirect, url_for, flash, jsonify
from jinja2  import TemplateNotFound
import os
import json
from dotenv import load_dotenv

# Database imports
import pymysql
from pymysql.cursors import DictCursor

# Load environment variables from .env file
load_dotenv()

# OpenAI imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# App modules
from app import app
# from app.models import Profiles

# Initialize OpenAI client with custom base URL and model if available
openai_client = None
if OPENAI_AVAILABLE:
    api_key = os.getenv('OPENAI_API_KEY')
    api_base = os.getenv('OPENAI_API_BASE')
    if api_key:
        openai_client = OpenAI(
            api_key=api_key,
            base_url=api_base
        )

# Database connection helper
def get_db_connection():
    """Create and return a connection to BIT 4444 Group Project database"""
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST', 'mysql'),
            port=int(os.getenv('DB_PORT', 3309)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'change-me'),
            database=os.getenv('DB_NAME', 'BIT 4444 Group Project'),
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=True
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Helper function to get database schema context for the AI
def get_database_context():
    """Get database tables and basic schema info for the AI context"""
    context = "Available Northwind database tables: "
    try:
        conn = get_db_connection()
        if not conn:
            return context + "Unable to connect to database."
        
        cursor = conn.cursor()
        # Get all table names
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s
        """, (os.getenv('DB_NAME', 'northwind'),))
        
        tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
        context += ", ".join(tables) if tables else "No tables found"
        
        conn.close()
    except Exception as e:
        context += f"(Error retrieving schema: {str(e)})"
    
    return context

# App main route + generic routing
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

# AI Chat routes
@app.route('/ai-chat')
def ai_chat():
    """Render the AI chat interface"""
    return render_template('ai_chat.html')

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Handle chat messages and call OpenAI API with Northwind database context"""
    try:
        # Check if OpenAI is configured
        if not openai_client:
            return jsonify({'error': 'OpenAI API not configured'}), 500
        
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        # Get model from environment or use default
        model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        # Get database context for the AI
        db_context = get_database_context()
        
        # Build system prompt with database info
        system_prompt = f"""You are a helpful assistant with access to a Northwind database.
You can answer questions about products, customers, orders, suppliers, employees, and more.

{db_context}

When users ask about data, you can help them understand the database or suggest SQL queries.
Be friendly and helpful in your responses."""
        
        # Debug: Print connection info (remove in production)
        print(f"[DEBUG] Using model: {model}")
        print(f"[DEBUG] API Base: {os.getenv('OPENAI_API_BASE')}")
        print(f"[DEBUG] User message: {user_message}")
        
        # Call OpenAI API
        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            reply = response.choices[0].message.content
            return jsonify({'reply': reply})
        
        except Exception as api_error:
            error_msg = str(api_error)
            print(f"[ERROR] OpenAI API call failed: {error_msg}")
            
            # Check for common auth errors
            if "401" in error_msg or "Unauthorized" in error_msg:
                return jsonify({
                    'error': 'Authentication failed. Check OPENAI_API_KEY and OPENAI_API_BASE in .env',
                    'details': error_msg
                }), 401
            elif "404" in error_msg:
                return jsonify({
                    'error': 'Model or endpoint not found. Check OPENAI_MODEL and OPENAI_API_BASE',
                    'details': error_msg
                }), 404
            else:
                return jsonify({'error': f'API Error: {error_msg}'}), 500
    
    except Exception as e:
        print(f"[ERROR] Chat endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/query', methods=['POST'])
def query_database():
    """Execute a database query and return results (for advanced users)"""
    try:
        data = request.get_json()
        sql_query = data.get('query', '').strip()
        
        if not sql_query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Safety check: only allow SELECT queries
        if not sql_query.upper().startswith('SELECT'):
            return jsonify({'error': 'Only SELECT queries are allowed'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        conn.close()
        
        return jsonify({'results': results, 'count': len(results)})
    
    except Exception as e:
        print(f"Query error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/db-info', methods=['GET'])
def db_info():
    """Get database schema and table information"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s
        """, (os.getenv('DB_NAME', 'northwind'),))
        
        tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
        
        # Get table info
        table_info = {}
        for table in tables:
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            table_info[table] = [
                {
                    'name': col.get('Field'),
                    'type': col.get('Type'),
                    'null': col.get('Null'),
                    'key': col.get('Key'),
                    'default': col.get('Default')
                }
                for col in columns
            ]
        
        conn.close()
        
        return jsonify({'tables': tables, 'schema': table_info})
    
    except Exception as e:
        print(f"DB info error: {e}")
        return jsonify({'error': str(e)}), 500

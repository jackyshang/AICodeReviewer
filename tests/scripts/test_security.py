#!/usr/bin/env python3
"""Test file with obvious security issues for testing the review tool."""

import os
import subprocess
import sqlite3

def vulnerable_sql_query(user_id):
    """SQL injection vulnerability."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # CRITICAL: SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    return cursor.fetchall()

def insecure_command_execution(filename):
    """Command injection vulnerability."""
    # CRITICAL: Command injection vulnerability
    os.system(f"cat {filename}")

def store_password(password):
    """Storing password in plain text."""
    # CRITICAL: Password stored in plain text
    with open('passwords.txt', 'a') as f:
        f.write(password + '\n')

def minor_style_issue():
    """This has only minor style issues."""
    x=1  # Missing spaces around operator
    if(x==1):  # Unnecessary parentheses
        print("Hello")
    return

# Unused import (suggestion level)
import json
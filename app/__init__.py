import os
from flask import Flask, request, session, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    
    app.config.from_object('config.Config')
    
    db.init_app(app)
    csrf.init_app(app)
    
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.manager import manager_bp
    from app.routes.public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(manager_bp, url_prefix='/manager')
    
    # LÓGICA GLOBAL DE MANUTENÇÃO
    @app.route('/maintenance')
    def maintenance_page():
        return render_template('public/maintenance.html')

    @app.before_request
    def check_maintenance_mode():
        flag_path = os.path.join(app.root_path, '..', 'maintenance.flag')
        is_maintenance = os.path.exists(flag_path)
        allowed_endpoints = [
            'auth.login', 
            'auth.setup_password', 
            'maintenance_page', 
            'static', 
            'manager.engineer_dashboard', 
            'manager.toggle_maintenance_mode'
        ]
        if is_maintenance and request.endpoint and request.endpoint not in allowed_endpoints:
            if session.get('role') != 'Engineer':
                return redirect(url_for('maintenance_page'))

    return app
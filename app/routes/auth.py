from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User, db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()

        if not username:
            flash("Please enter your RA Username.", "danger")
            return redirect(url_for('auth.login'))

        # Procura o utilizador no banco
        user = User.query.filter_by(ra_username=username).first()

        # Se não existir, a nossa "mágica" cria-o na hora com o cargo certo!
        if not user:
            # Regra VIP para a apresentação
            if username.lower() == 'timecrush':
                role = 'manager'
            else:
                role = 'playtester' # Qualquer outro nick (incluindo cnat) vira tester

            user = User(ra_username=username, role=role)
            db.session.add(user)
            db.session.commit()

        # Guarda na sessão do navegador
        session['user_id'] = user.id
        session['username'] = user.ra_username
        session['role'] = user.role

        flash(f"Welcome, {user.ra_username}!", "success")

        # Redireciona o TimeCrush para o Manager e os outros para o Dashboard
        if user.role == 'manager':
            return redirect(url_for('manager.index'))
        else:
            return redirect(url_for('dashboard.index'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear() # Apaga a memória de quem estava logado
    return redirect(url_for('auth.login'))
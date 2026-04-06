from datetime import datetime
from app import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    ra_username = db.Column(db.String(100), unique=True, nullable=False)
    discord_id = db.Column(db.String(100), unique=True, nullable=True) # Caso precise no futuro
    role = db.Column(db.String(20), default='playtester') # playtester, cr, manager
    is_active = db.Column(db.Boolean, default=True)
    
    # Relacionamento: Um usuário pode ter várias sessões de teste
    sessions = db.relationship('TestSession', backref='tester', lazy=True)

class Game(db.Model):
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    developer = db.Column(db.String(100), nullable=False)
    developer_level = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Open')
    is_collab = db.Column(db.Boolean, default=False)
    image_icon = db.Column(db.String(100), nullable=True)
    console_name = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    achievements = db.relationship('Achievement', backref='game', lazy=True, cascade="all, delete-orphan")
    test_sessions = db.relationship('TestSession', backref='game', lazy=True)

class Achievement(db.Model):
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True) # ID oficial da conquista no RA
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, default=0)
    
    # Relacionamento com os resultados
    results = db.relationship('TestResult', backref='achievement', lazy=True)

class TestSession(db.Model):
    __tablename__ = 'test_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    
    # Condições do teste preenchidas pelo playtester
    core = db.Column(db.String(100), nullable=True)
    hash_used = db.Column(db.String(100), nullable=True)
    
    status = db.Column(db.String(20), default='Active') # Active, Concluded, Abandoned
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True) # Para a regra de 1 semana do SLA
    
    # Relacionamento
    results = db.relationship('TestResult', backref='session', lazy=True, cascade="all, delete-orphan")

class TestResult(db.Model):
    __tablename__ = 'test_results'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('test_sessions.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    
    # Estados: None (não testado), OK, FALSE_TRIGGER, NO_TRIGGER, OK_AFTER_RETEST
    trigger_status = db.Column(db.String(20), nullable=True) 
    notes = db.Column(db.Text, nullable=True)
    save_state_link = db.Column(db.String(500), nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def atualizar_cargo_do_usuario(user, permissoes_do_ra):
    
    if 'Playtest Manager' in permissoes_do_ra or 'Quality Assurance' in permissoes_do_ra:
        user.role = 'manager'  # Acesso total, importa jogos
    elif 'Code Reviewer' in permissoes_do_ra:
        user.role = 'cr'       # Acesso ao painel de raio-x
    elif 'Play Tester' in permissoes_do_ra:
        user.role = 'playtester' # Acesso ao dashboard de testes
    else:
        user.role = 'bloqueado'  # Usuário comum do RA que não faz parte da equipe
    db.session.commit()
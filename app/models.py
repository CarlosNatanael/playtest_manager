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
    developer_id = db.Column(db.Integer, nullable=True)
    developer_level = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Open')
    is_collab = db.Column(db.Boolean, default=False)
    image_icon = db.Column(db.String(100), nullable=True)
    console_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    achievements = db.relationship('Achievement', backref='game', lazy=True, cascade="all, delete-orphan")
    test_sessions = db.relationship('TestSession', backref='game', lazy=True)

    def get_console_icon(self):
        """Traduz o nome do console salvo no banco para o nome da imagem do RA"""
        mapping = {
        'Atari 2600': '2600',
        '32X': '32x',
        '3DO': '3do',
        'Nintendo 3DS': '3ds',
        'Atari 5200': '5200',
        'Atari 7800': '7800',
        'IBM PC 8088': '8088',
        'NEC PC-9800': '9800',
        'Apple II': 'a2',
        'Commodore Amiga': 'amiga',
        'Commodore 64': 'c64',
        'Philips CD-i': 'cd-i',
        'CHIP-8': 'chip-8',
        'Amstrad CPC': 'cpc',
        'ColecoVision': 'cv',
        'Sega Dreamcast': 'dc',
        'DEC Mate': 'decmate',
        'MS-DOS': 'dos',
        'Nintendo DS': 'ds',
        'Nintendo DSi': 'dsi',
        'Nintendo Famicom Disk System': 'fds',
        'FM Towns': 'fm-towns',
        'Game & Watch': 'g&w',
        'Nintendo Game Boy': 'gb',
        'Nintendo Game Boy Advance': 'gba',
        'Nintendo Game Boy Color': 'gbc',
        'Nintendo GameCube': 'gc',
        'Sega Game Gear': 'gg',
        'Intellivision': 'intv',
        'Atari Jaguar': 'jag',
        'Atari Lynx': 'lynx',
        'Sega Mega Drive': 'md',
        'MSX': 'msx',
        'Nokia N-Gage': 'n-gage',
        'Nintendo 64': 'n64',
        'Nintendo Entertainment System': 'nes',
        'Neo Geo CD': 'ngcd',
        'Neo Geo Pocket': 'ngp',
        'PC-FX': 'pc-fx',
        'NEC PC Engine': 'pce',
        'PICO-8': 'pico-8',
        'Sega Pico': 'pico',
        'PlayStation': 'ps1',
        'PlayStation 2': 'ps2',
        'PlayStation 3': 'ps3',
        'PlayStation Portable': 'psp',
        'Sega Saturn': 'sat',
        'Sega CD': 'scd',
        'Sega Master System': 'sms',
        'Super Nintendo Entertainment System': 'snes',
        'TI-83': 'ti-83',
        'TIC-80': 'tic-80',
        'Wii': 'wii',
        'Wii U': 'wiiu',
        'WonderSwan': 'ws',
        'Xbox': 'xbox',
        'ZX81': 'zx81',
        'ZX Spectrum': 'zxs'
        }
        return mapping.get(self.console_name, 'unknown')

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
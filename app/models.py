from datetime import datetime
from app import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    ra_username = db.Column(db.String(100), unique=True, nullable=False)
    image_username = db.Column(db.String(100), nullable=True)
    discord_id = db.Column(db.String(100), unique=True, nullable=True)
    role = db.Column(db.String(20), default='playtester')
    is_active = db.Column(db.Boolean, default=True)
    event_progress = db.relationship('UserEventProgress', backref='tester_progress', lazy=True)
    
    password_hash = db.Column(db.String(255), nullable=True)
    invite_token = db.Column(db.String(100), unique=True, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    
    sessions = db.relationship('TestSession', backref='tester', lazy=True)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        if not self.password_hash or self.password_hash == 'PENDING_INVITE':
            return False
            
        return check_password_hash(self.password_hash, password)

class Game(db.Model):
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    title = db.Column(db.String(150), nullable=False)
    developer = db.Column(db.String(100), nullable=True)
    developer_level = db.Column(db.String(20), default='Junior')
    developer_pic = db.Column(db.String(255), nullable=True)
    console_name = db.Column(db.String(50), nullable=True)
    image_icon = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='Open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_collab = db.Column(db.Boolean, default=False)
    collab_locked = db.Column(db.Boolean, default=False)
    
    achievements = db.relationship('Achievement', backref='game', lazy=True, cascade="all, delete-orphan")
    test_sessions = db.relationship('TestSession', backref='game', lazy=True, cascade="all, delete-orphan")

    def get_console_icon(self):
        """Traduz o nome do console salvo no banco para o nome da imagem do RA"""
        mapping = {
        'Arcade': 'arc',
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
        'Dreamcast': 'dc',
        'DEC Mate': 'decmate',
        'MS-DOS': 'dos',
        'Nintendo DS': 'ds',
        'Nintendo DSi': 'dsi',
        'Famicom Disk System': 'fds',
        'FM Towns': 'fm-towns',
        'Game & Watch': 'g&w',
        'Game Boy': 'gb',
        'Game Boy Advance': 'gba',
        'Game Boy Color': 'gbc',
        'GameCube': 'gc',
        'Game Gear': 'gg',
        'Intellivision': 'intv',
        'Atari Jaguar': 'jag',
        'Atari Lynx': 'lynx',
        'Genesis/Mega Drive': 'md',
        'MSX': 'msx',
        'Nokia N-Gage': 'n-gage',
        'Nintendo 64': 'n64',
        'NES/Famicom': 'nes',
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
        'Saturn': 'sat',
        'Sega CD': 'scd',
        'Master System': 'sms',
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
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    badge_name = db.Column(db.String(50))
    points = db.Column(db.Integer, default=0)
    
    results = db.relationship('TestResult', backref='achievement', lazy=True)

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    badge_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    
    challenges = db.relationship('EventChallenge', backref='event', lazy=True, cascade="all, delete-orphan")

class EventChallenge(db.Model):
    __tablename__ = 'event_challenges'
    id = db.Column(db.Integer, primary_key=True)
    badge_url = db.Column(db.String(255), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    challenge_type = db.Column(db.String(50), nullable=False) 
    target_value = db.Column(db.Integer, default=1)
    points = db.Column(db.Integer, default=10)
    
    progress = db.relationship('UserEventProgress', backref='challenge', lazy=True, cascade="all, delete-orphan")

class UserEventProgress(db.Model):
    __tablename__ = 'user_event_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('event_challenges.id'), nullable=False)
    
    current_value = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)

class TestSession(db.Model):
    __tablename__ = 'test_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_collab = db.Column(db.Boolean, default=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)

    emulator = db.Column(db.String(100), nullable=True)
    core = db.Column(db.String(100), nullable=True)
    hash_used = db.Column(db.String(100), nullable=True)
    checklist_data = db.Column(db.Text, nullable=True)
    set_impressions = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.String(20), default='Active')
    concluded_at = db.Column(db.DateTime, nullable=True) 
    expires_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    results = db.relationship('TestResult', backref='session', lazy=True, cascade="all, delete-orphan")

    @property
    def days_remaining(self):
        if self.expires_at:
            delta = self.expires_at - datetime.utcnow()
            return delta.days
        return None

class TestResult(db.Model):
    __tablename__ = 'test_results'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('test_sessions.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    trigger_status = db.Column(db.String(20), nullable=True)
    previous_status = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    save_state_link = db.Column(db.String(500), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GameLog(db.Model):
    __tablename__ = 'game_logs'

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    game = db.relationship('Game', backref=db.backref('logs', lazy=True, cascade="all, delete-orphan"))
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'  # Necesario para mensajes flash

def get_db_connection():
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            nombre_usuario TEXT UNIQUE NOT NULL,
            documento TEXT UNIQUE NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL,
            rol TEXT DEFAULT 'rol_usuario',
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
            activo INTEGER DEFAULT 1
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            fecha_inicio DATE,
            fecha_fin DATE,
            estado TEXT DEFAULT 'activo',
            id_usuario_creador INTEGER,
            FOREIGN KEY (id_usuario_creador) REFERENCES usuarios(id) ON DELETE SET NULL
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            fecha_vencimiento DATE,
            prioridad TEXT,
            estado TEXT DEFAULT 'pendiente',
            id_proyecto INTEGER,
            id_usuario_asignado INTEGER,
            ruta_archivo TEXT,
            FOREIGN KEY (id_proyecto) REFERENCES proyectos(id) ON DELETE CASCADE,
            FOREIGN KEY (id_usuario_asignado) REFERENCES usuarios(id) ON DELETE SET NULL
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensaje TEXT NOT NULL,
            leido INTEGER DEFAULT 0,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            id_usuario INTEGER,
            FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE
        );
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_nombre_usuario ON usuarios(nombre_usuario);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_documento ON usuarios(documento);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_correo ON usuarios(correo);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tareas_id_usuario_asignado ON tareas(id_usuario_asignado);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_proyectos_id_usuario_creador ON proyectos(id_usuario_creador);')

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contraseña']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE nombre_usuario = ? AND contrasena = ?', (usuario, contrasena)).fetchone()
        conn.close()

        if user:
            # Login correcto, redirige a admin
            return redirect(url_for('admin'))
        else:
            # Login fallido, vuelve a mostrar login con mensaje
            flash('Usuario o contraseña incorrectos')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/crear_usuario', methods=['GET', 'POST'])
def crear_usuario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        nombre_usuario = request.form['usuario']
        documento = request.form['documento']
        correo = request.form['correo']
        contrasena = request.form['contraseña']

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO usuarios (nombre, nombre_usuario, documento, correo, contrasena)
            VALUES (?, ?, ?, ?, ?)
        ''', (nombre, nombre_usuario, documento, correo, contrasena))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('crear_usuario.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
DATABASE = 'usuarios.db'

# Función de conexión a la base de datos
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Inicializar base de datos con tablas

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            nombre_usuario TEXT UNIQUE NOT NULL,
            curso TEXT NOT NULL,
            documento TEXT UNIQUE NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL,
            rol TEXT DEFAULT 'rol_usuario',
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
            activo INTEGER DEFAULT 1,
            tema TEXT DEFAULT 'claro',
            idioma TEXT DEFAULT 'es',
            notificaciones INTEGER DEFAULT 1
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
            curso_destino TEXT,
            FOREIGN KEY (id_proyecto) REFERENCES proyectos(id) ON DELETE CASCADE,
            FOREIGN KEY (id_usuario_asignado) REFERENCES usuarios(id) ON DELETE SET NULL
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
        CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensaje TEXT NOT NULL,
            leido INTEGER DEFAULT 0,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            id_usuario INTEGER,
            FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE
        );
    ''')

    hashed_admin = generate_password_hash('admin123')
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (nombre, nombre_usuario, curso, documento, correo, contrasena, rol, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('Administrador', 'admin', 'N/A', '00000000', 'admin@example.com', hashed_admin, 'rol_administrador', 1))

    hashed_profesor = generate_password_hash('profesor123')
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (nombre, nombre_usuario, curso, documento, correo, contrasena, rol, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('Profesor Juan', 'profesor1', 'Matemáticas', '12345678', 'profesor1@example.com', hashed_profesor, 'rol_profesor', 1))

    conn.commit()
    conn.close()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Usuario(UserMixin):
    def __init__(self, id, nombre, nombre_usuario, curso, documento, correo, contrasena, rol, fecha_registro, activo):
        self.id = id
        self.nombre = nombre
        self.nombre_usuario = nombre_usuario
        self.curso = curso
        self.documento = documento
        self.correo = correo
        self.contrasena = contrasena
        self.rol = rol
        self.fecha_registro = fecha_registro
        self.activo = activo

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    fila = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if fila:
        return Usuario(
            id=fila['id'],
            nombre=fila['nombre'],
            nombre_usuario=fila['nombre_usuario'],
            curso=fila['curso'],
            documento=fila['documento'],
            correo=fila['correo'],
            contrasena=fila['contrasena'],
            rol=fila['rol'],
            fecha_registro=fila['fecha_registro'],
            activo=fila['activo']
        )
    return None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['nombre_usuario']
        contrasena = request.form['contrasena']
        conn = get_db_connection()
        fila = conn.execute('SELECT * FROM usuarios WHERE nombre_usuario = ?', (usuario,)).fetchone()
        conn.close()
        if fila and check_password_hash(fila['contrasena'], contrasena) and fila['activo']:
            user = Usuario(
                id=fila['id'],
                nombre=fila['nombre'],
                nombre_usuario=fila['nombre_usuario'],
                curso=fila['curso'],
                documento=fila['documento'],
                correo=fila['correo'],
                contrasena=fila['contrasena'],
                rol=fila['rol'],
                fecha_registro=fila['fecha_registro'],
                activo=fila['activo']
            )
            login_user(user)
            if user.rol == 'rol_administrador':
                return redirect(url_for('admin'))
            elif user.rol == 'rol_profesor':
                return redirect(url_for('profesor'))
            else:
                return redirect(url_for('persona'))

        flash('Usuario o contraseña incorrectos')
    return render_template('login.html')

@app.route('/crear_usuario', methods=['GET', 'POST'])
def crear_usuario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        nombre_usuario = request.form['nombre_usuario']
        curso = request.form['curso']
        documento = request.form['documento']
        correo = request.form['correo']
        contrasena = generate_password_hash(request.form['contrasena'])
        rol = request.form.get('rol', 'rol_usuario')
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO usuarios (nombre, nombre_usuario, curso, documento, correo, contrasena, rol)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, nombre_usuario, curso, documento, correo, contrasena, rol))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El nombre de usuario, documento o correo ya existe')
        finally:
            conn.close()
    return render_template('crear_usuario.html')

@app.route('/profesor')
@login_required
def profesor():
    if current_user.rol != 'rol_profesor':
        flash('Acceso denegado')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursos = conn.execute('SELECT DISTINCT curso FROM usuarios WHERE rol = "rol_usuario" AND activo = 1').fetchall()
    conn.close()
    return render_template('profesor.html', cursos=cursos)

@app.route('/crear_tarea_profesor', methods=['POST'])
@login_required
def crear_tarea_profesor():
    if current_user.rol != 'rol_profesor':
        flash('Acceso denegado')
        return redirect(url_for('index'))

    titulo = request.form['titulo']
    descripcion = request.form['descripcion']
    curso_destino = request.form['curso_destino']
    archivo = request.files['archivo']
    ruta_archivo = ''

    if archivo and archivo.filename:
        nombre_archivo = secure_filename(archivo.filename)
        ruta_archivo = os.path.join('archivos_tareas', nombre_archivo)
        archivo.save(ruta_archivo)

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO tareas (titulo, descripcion, curso_destino, ruta_archivo, id_usuario_asignado)
        VALUES (?, ?, ?, ?, ?)
    ''', (titulo, descripcion, curso_destino, ruta_archivo, current_user.id))

    estudiantes = conn.execute('SELECT id FROM usuarios WHERE curso = ? AND rol = "rol_usuario" AND activo = 1', (curso_destino,)).fetchall()
    for est in estudiantes:
        mensaje = f'Se ha creado una nueva tarea para tu curso: {titulo}'
        conn.execute('INSERT INTO notificaciones (mensaje, id_usuario) VALUES (?, ?)', (mensaje, est['id']))

    conn.commit()
    conn.close()

    flash('Tarea creada correctamente')
    return redirect(url_for('profesor'))

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/persona')
@login_required
def persona():
    return render_template('persona.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/ajustes', methods=['POST'])
@login_required
def ajustes():
    tema = request.form.get('tema')
    idioma = request.form.get('idioma')
    notificaciones = 1 if request.form.get('notificaciones') == 'on' else 0
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE usuarios SET tema = ?, idioma = ?, notificaciones = ? WHERE id = ?
        ''', (tema, idioma, notificaciones, current_user.id))
        conn.commit()
        conn.close()
        return 'OK'
    except Exception as e:
        print("Error al guardar ajustes:", e)
        return 'Error al guardar ajustes', 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

from flask import Flask, request, render_template, redirect, url_for, session, g
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'nutri_clave_2026'

# --- CONEXIÓN LIMPIA ---
def get_db():
    if 'db' not in g:
        # Conexión directa a MongoDB
        client = MongoClient('mongodb://127.0.0.1:27017/')
        g.db = client['gestor_tareas']
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.client.close()

# --- RUTAS DE ACCESO ---

@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('ver_tareas'))
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        db = get_db()
        # Captura de los 5 datos
        nuevo_usuario = {
            "nombre": request.form.get('nombre'),
            "email": request.form.get('email'),
            "password": request.form.get('password'),
            "genero": request.form.get('genero'),
            "fecha_nacimiento": request.form.get('fecha_nac'),
            "fecha_registro": datetime.now()
        }
        # Insertar y redirigir al login
        db.usuarios.insert_one(nuevo_usuario)
        return redirect(url_for('index'))
    return render_template('registro.html')

@app.route('/sesion', methods=['POST'])
def inicio_sesion():
    db = get_db()
    email = request.form.get('email')
    password = request.form.get('password')
    
    user = db.usuarios.find_one({"email": email, "password": password})
    if user:
        session['usuario_id'] = str(user['_id'])
        session['usuario_nombre'] = user['nombre']
        return redirect(url_for('ver_tareas'))
    return redirect(url_for('index'))

# --- RUTAS DE LA APP (LOGUEADO) ---

@app.route('/tareas', methods=['GET', 'POST'])
def ver_tareas():
    if 'usuario_id' not in session: return redirect(url_for('index'))
    db = get_db()
    
    if request.method == 'POST':
        db.tareas.insert_one({
            "usuario_id": ObjectId(session['usuario_id']),
            "descripcion": request.form.get('tarea'),
            "fecha": datetime.now()
        })
    
    mis_tareas = list(db.tareas.find({"usuario_id": ObjectId(session['usuario_id'])}))
    return render_template('tareas.html', tareas=mis_tareas)

@app.route('/perfil')
def ver_perfil():
    if 'usuario_id' not in session: return redirect(url_for('index'))
    db = get_db()
    user_data = db.usuarios.find_one({"_id": ObjectId(session['usuario_id'])})
    return render_template('ver_perfil.html', u=user_data)

@app.route('/editar', methods=['GET', 'POST'])
def editar_perfil():
    if 'usuario_id' not in session: return redirect(url_for('index'))
    db = get_db()
    uid = ObjectId(session['usuario_id'])

    if request.method == 'POST':
        db.usuarios.update_one({"_id": uid}, {"$set": {
            "nombre": request.form.get('nombre'),
            "email": request.form.get('email'),
            "genero": request.form.get('genero'),
            "fecha_nacimiento": request.form.get('fecha_nac')
        }})
        session['usuario_nombre'] = request.form.get('nombre')
        return redirect(url_for('ver_perfil'))

    user_data = db.usuarios.find_one({"_id": uid})
    return render_template('editar_perfil.html', u=user_data)

@app.route('/eliminar/<id>')
def eliminar(id):
    if 'usuario_id' in session:
        get_db().tareas.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('ver_tareas'))

@app.route('/salir')
def salir():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
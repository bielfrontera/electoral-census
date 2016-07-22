# coding: utf-8
import pymssql
from flask import current_app as app
from datetime import datetime, date
from Crypto.Cipher import AES
import base64
from pyjon.reports import ReportFactory
import tempfile


class BaseError(Exception):
    def __init__(self, error_code, error_desc, status_code):
        self.error_code = error_code
        self.error_desc = error_desc
        self.status_code = status_code

    def to_dict(self):
        return {
            'error_code': self.error_code,
            'error_desc': self.error_desc,
        }


class NifRequiredError(BaseError):
    pass


class InvalidNifError(BaseError):
    pass


class BirthdateRequiredError(BaseError):
    pass


class InvalidBirthdateError(BaseError):
    pass


class Voter:
    def __init__(self, nif, district, section, table, school, address):
        self.nif = nif
        self.district = district
        self.section = section
        self.table = table
        self.school = school
        self.address = address

    def to_dict(self):
        return {
            'nif': self.nif,
            'district': self.district,
            'section': self.section,
            'table': self.table,
            'school': self.school,
            'address': self.address,
        }

    @classmethod
    def from_row(cls, nif, row):
        district = row[2]
        section = row[3]
        table = row[4]
        school = row[0]
        address = row[1]

        return cls(nif, district, section, table, school, address)


class InhabitantCertificate:
    def __init__(self, dboid, decode=False):
        self.dboid = dboid
        self.date = date.today()
        if decode:
            codi = self.decode(dboid)
            if '#' in codi:
                self.dboid = codi.split('#')[0]
                self.date = datetime.strptime(codi.split('#')[1], '%Y%m%d')
            else:
                self.dboid = codi

    def encode(self, value):
        cipher = AES.new(app.config["SECRET_KEY"].zfill(16), AES.MODE_ECB)
        encoded = base64.urlsafe_b64encode(cipher.encrypt(str(value).rjust(32)))
        return encoded

    def decode(self, value):
        cipher = AES.new(app.config["SECRET_KEY"].zfill(16), AES.MODE_ECB)
        decoded = cipher.decrypt(base64.urlsafe_b64decode(value.encode("utf-8")))
        return decoded.strip()

    def to_dict(self):
        codi = "{}#{}".format(
            str(self.dboid),
            date.today().strftime('%Y%m%d'))
        codi = self.encode(codi)
        return {
            'url_certificat': '/certificat-viatge/certificat-viatge.pdf?codi=' + codi
        }

    @classmethod
    def from_row(cls, row):
        dboid = row[0]
        return cls(dboid)


class ElectoralCensus:

    @classmethod
    def find_by_nif(cls, nif):

        if not nif:
            raise NifRequiredError('bad_request', 'El camp DNI és obligatori', 400)

        if len(nif) < 8:
            raise InvalidNifError('bad_request', 'El camp DNI no té la longitud mínima', 400)

        query = """
            SELECT C.COLDESCRI, C.COLDOMIC, M.MESDISTRI, M.MESSECCIO, M.MESMESA, E.ELEMESA
            FROM
            ELEELECTO E, ELEMESAS M, ELECOLEGI C
            wHERE
            C.COLCODIGO=M.MESCOLEGI AND
            M.MESELECCI='{elec}' AND
            M.MESMESA = E.ELEMESA AND
            M.MESDISTRI = E.ELEDISTRI AND
            M.MESSECCIO = E.ELESECCIO AND
            E.ELEMESA=M.MESMESA AND
            E.ELEIDEN=%s AND
            E.ELEELECCI='{elec}';
        """.format(
            elec=app.config["ELE_CODIELE"])
        
        try:
            conn = pymssql.connect(host=app.config["ELE_DBHOST"], user=app.config["ELE_DBUSER"],
                                   password=app.config["ELE_DBPASS"], database=app.config["ELE_DBNAME"],
                                   timeout=5, login_timeout=5)
            cursor = conn.cursor()
            search_nif = nif[0:8]
            cursor.execute(query, search_nif)
            rows = cursor.fetchall()
        except Exception as e:
            raise BaseError('bad_request', 'Error a l\'aplicació. Torni-ho a provar en uns moments o telefoni a l\'Ajuntament d\'Inca: {e}'.format(e=str(e)), 400)
        finally:
            conn.close()

        if not rows:
            raise InvalidNifError('bad_request', 'DNI {nif} no trobat a la base de dades d\'electors'.format(nif=nif), 400)
        voter = Voter.from_row(nif, rows[0])

        return voter


class CertificatViatge:

    @classmethod
    def get_certificate_url(cls, nif, birthdate):

        if not nif:
            raise NifRequiredError('bad_request', 'El camp DNI és obligatori', 400)

        if len(nif) < 9:
            raise InvalidNifError('bad_request', 'El camp DNI no té la longitud mínima', 400)

        if not birthdate:
            raise BirthdateRequiredError('bad_request', 'El camp Data de naixement és obligatori', 400)

        try:
            search_birthdate = datetime.strptime(birthdate, '%d/%m/%Y')
        except ValueError:
            raise InvalidBirthdateError('bad_request', 'El camp Data de naixement no té el format correcte', 400)

        # UE countries + EEE (Islandia, Liechtenstein, Noruega) + Suissa
        query = """
            SELECT DISTINCT SP_POB_HABITA.HABDBOIDE
            FROM SP_POB_HABITA, PAIS_ELEC, SP_BDC_PAISES
            WHERE SP_POB_HABITA.HABVIGENT='T' AND
            SP_POB_HABITA.HABOIDULT Is Null AND
            SP_POB_HABITA.HABNUMIDE=%s AND
            SP_POB_HABITA.HABCONDIG=%s AND
            SP_POB_HABITA.HABFECNAC=%s AND
            PAIS_ELEC.PELCODNAC = SP_BDC_PAISES.PAICODPAI AND
            (PAIS_ELEC.PELTIPELE = 'CE' OR
            SP_BDC_PAISES.PAICODPAI IN (114, 116, 120, 132));
        """
        conn = None
        try:
            conn = pymssql.connect(host=app.config["HABITA_DBHOST"], user=app.config["HABITA_DBUSER"],
                                   password=app.config["HABITA_DBPASS"], database=app.config["HABITA_DBNAME"],
                                   timeout=5, login_timeout=5)
            cursor = conn.cursor()
            search_nif = nif[0:-1].upper()
            if search_nif[0].isdigit():
                search_nif = search_nif.zfill(9)
            search_cc = nif[-1:].upper()
            cursor.execute(query, (search_nif, search_cc, search_birthdate))
            rows = cursor.fetchall()
        except Exception as e:
            raise BaseError('internal_server_error', 'Error a l\'aplicació. Torni-ho a provar en uns moments o telefoni a l\'Ajuntament d\'Inca: {e}'.format(
                e=str(e)), 500)
        finally:
            if conn:
                conn.close()

        if not rows:
            raise InvalidNifError('bad_request', 'No s\'ha trobat cap persona al padró actual amb DNI {} i data de naixement {}'.format(
                nif, birthdate), 400)
        record = InhabitantCertificate.from_row(rows[0])
        return record

    @classmethod
    def generate_certificate(cls, dboid, url):
        record = InhabitantCertificate(dboid, decode=True)

        query = """
            SELECT SP_POB_HABITA.HABNOMCOM, SP_POB_HABITA.HABNUMIDE, SP_POB_HABITA.HABCONDIG,
            SP_BDC_PAISES.PAINOMPAI, SP_POB_HABITA.HABFECNAC
            FROM SP_POB_HABITA INNER JOIN SP_BDC_PAISES ON SP_POB_HABITA.HABNACION = SP_BDC_PAISES.PAICODPAI
            WHERE SP_POB_HABITA.HABVIGENT='T' AND
            SP_POB_HABITA.HABOIDULT Is Null AND
            SP_POB_HABITA.HABDBOIDE=%s;
        """
        conn = None
        try:
            conn = pymssql.connect(host=app.config["HABITA_DBHOST"], user=app.config["HABITA_DBUSER"],
                                   password=app.config["HABITA_DBPASS"], database=app.config["HABITA_DBNAME"],
                                   timeout=5, login_timeout=5)
            cursor = conn.cursor()
            cursor.execute(query, (record.dboid, ))
            rows = cursor.fetchall()
        except Exception as e:
            raise BaseError('internal_server_error', 'Error a l\'aplicació. Torni-ho a provar en uns moments o telefoni a l\'Ajuntament d\'Inca: {e}'.format(
                e=str(e)), 500)
        finally:
            if conn:
                conn.close()

        if not rows:
            raise InvalidNifError('bad_request', 'No s\'ha trobat cap persona al padró actual amb DBOID {}'.format(
                record.dboid), 400)

        template = 'templates/certificat-viatge.xml'
        person = {}
        person['name'] = rows[0][0].replace('*', ' ').replace(',', ', ')
        person['id'] = "{}{}".format(rows[0][1], rows[0][2])
        person['nationality'] = rows[0][3]

        factory = ReportFactory()
        factory.render_template(template_file=template,
                                person=person,
                                today=record.date,
                                url_doc=url)
        tf = tempfile.NamedTemporaryFile()
        factory.render_document(tf.name)
        factory.cleanup()
        return tf

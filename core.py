# coding: utf-8
import pymssql


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


class ElectoralCensus:
    CODIELECCI = '7294868E2A1544759AD5C2C257395DA1'

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
            elec=cls.CODIELECCI)

        try:
            conn = pymssql.connect(host='host', user='user', password='secret', database="database")
            cursor = conn.cursor()
            search_nif = nif[0:8]
            cursor.execute(query, search_nif)
            rows = cursor.fetchall()
        except Exception as e:
            raise BaseError('bad_request', 'Error a l\'aplicació. Torni-ho a provar en uns moments o telefoni a l\'Ajuntament d\'Inca: {e}'.format(e=str(e)) , 400)
        finally:
            conn.close()

        if not rows:
            raise InvalidNifError('bad_request', 'DNI {nif} no trobat a la base de dades d\'electors'.format(nif=nif), 400)
        voter = Voter.from_row(nif, rows[0])

        return voter

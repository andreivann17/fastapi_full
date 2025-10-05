# app/models/patients.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from ..db import get_connection

class PatientsModel:
    def code_exists(self, code: str) -> bool:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM patients WHERE code=%s LIMIT 1", (code,))
                return cur.fetchone() is not None
        finally:
            conn.close()

    def get_current_img_by_code(self, code: str) -> str:
        """Devuelve la ruta img actual para ese code (o cadena vacía)."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT img FROM patients WHERE code=%s", (code,))
                row = cur.fetchone()
                if not row:
                    raise ValueError("Patient not found")
                (img,) = row
                return img or ""
        finally:
            conn.close()

    def add_patient(
        self,
        *,
        code: str,
        first_name: str,
        last_name: str,
        email: str,               # <-- NUEVO
        gender_id: int,
        blood_type_id: int,
        birth_date: str,
        city: int,
        state: int,
        country: int,
        img: str,
        created_by: int,
    ) -> None:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO patients
                    (code, first_name, last_name, email, id_gender, id_blood_type, birth_date,
                     img, city, state, country,
                     wears_glasses, has_diabetes, has_hypertension, is_smoker,
                     eye_surgery_history, has_high_myopia, family_history_ocular_disease,
                     active, date, time, date_creation, time_creation, id_user)
                    VALUES
                    (%s, %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s,
                     0, 0, 0, 0,
                     0, 0, 0,
                     1, CURDATE(), CURTIME(), CURDATE(), CURTIME(), %s)
                    """,
                    (
                        code, first_name, last_name, email, gender_id, blood_type_id, birth_date,
                        img, city, state, country,
                        created_by,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
    def delete_patient(self, patient_id: int, user_id: int) -> None:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE patients
                       SET active = 0,
                           date   = CURDATE(),
                           time   = CURTIME(),
                           id_user = %s
                     WHERE id_patient = %s
                    """,
                    (user_id, patient_id),
                )
                conn.commit()
        finally:
            conn.close()

    def get_patients_cards(
        self,
        limit: int, search: str = "", offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Listado paginado para cards (incluye email y busca por email)."""
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                base = (
                    "SELECT id_patient AS id, code, CONCAT(first_name,' ',last_name) AS name, email "
                    "FROM patients WHERE active = 1"
                )
                params: List[Any] = []
                if search:
                    base += " AND (first_name LIKE %s OR last_name LIKE %s OR email LIKE %s)"
                    like = f"%{search}%"
                    params.extend([like, like, like])
                base += " ORDER BY id_patient DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cur.execute(base, tuple(params))
                return cur.fetchall()
        finally:
            conn.close()

patients_model = PatientsModel()

def get_gender_list() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT id_gender, name FROM genders ORDER BY id_gender ASC")
            return cur.fetchall()
    finally:
        conn.close()

def get_blood_type_list() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT id_blood_type, name FROM blood_type ORDER BY id_blood_type ASC")
            return cur.fetchall()
    finally:
        conn.close()

def get_patients(patient_id: Optional[int] = None) -> Dict[str, Any]:
    """Listado (o detalle) de pacientes + catálogos (incluye email)."""
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            if patient_id:
                cur.execute(
                    """
                    SELECT
                        p.id_patient,
                        p.code,
                        p.first_name,
                        p.last_name,
                        p.email,                 -- <-- NUEVO
                        p.id_gender,
                        p.id_blood_type,
                        p.birth_date,
                        p.date,
                        p.time,
                        p.date_creation,
                        p.time_creation,
                        p.id_user,
                        p.img,
                        p.city,
                        p.state,
                        p.wears_glasses,
                        p.has_diabetes,
                        p.has_hypertension,
                        p.is_smoker,
                        p.eye_surgery_history,
                        p.has_high_myopia,
                        p.family_history_ocular_disease
                    FROM patients p
                    WHERE p.active = 1 AND p.id_patient = %s
                    """,
                    (patient_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        p.id_patient,
                        p.code,
                        p.first_name,
                        p.last_name,
                        p.email,                 -- <-- NUEVO
                        p.id_gender,
                        p.id_blood_type,
                        p.birth_date,
                        p.date,
                        p.time,
                        p.date_creation,
                        p.time_creation,
                        p.id_user,
                        p.img,
                        p.city,
                        p.state,
                        p.wears_glasses,
                        p.has_diabetes,
                        p.has_hypertension,
                        p.is_smoker,
                        p.eye_surgery_history,
                        p.has_high_myopia,
                        p.family_history_ocular_disease
                    FROM patients p
                    WHERE p.active = 1
                    ORDER BY p.id_patient DESC
                    """
                )
            patients = cur.fetchall()
        genders = get_gender_list()
        blood_types = get_blood_type_list()
        return {"patients": patients, "dataGender": genders, "dataBloodType": blood_types}
    finally:
        conn.close()
def get_patient_by_code_sql(code: str) -> Optional[Dict[str, Any]]:
    """
    Devuelve un dict con el paciente + lookups por 'code'.
    Retorna None si no existe.
    """
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT
                    p.id_patient,
                    p.code,
                    p.first_name  AS firstName,
                    p.last_name   AS lastName,
                    p.email,
                    p.id_gender   AS idGender,
                    g.name        AS genderName,
             
                    p.birth_date    AS birthDate,
                    p.city, p.state, p.country,
                    p.img,
                    p.date_creation,
                    p.time_creation
                FROM patients p
                LEFT JOIN genders g      ON g.id_gender = p.id_gender
             
                WHERE p.code = %s
                LIMIT 1
                """,
                (code,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()
def edit_patient_by_code(data: Dict[str, Any], user_id: int) -> None:
    """
    Actualiza paciente usando code como identificador principal.
    Acepta: firstName, lastName, email, idGender, idBloodType (si lo usas), birthDate, img, city, state, code
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE patients
                   SET first_name    = %s,
                       last_name     = %s,
                       email         = %s,
                       id_gender     = %s,
                       id_blood_type = %s,
                       birth_date    = %s,
                       img           = %s,
                       city          = %s,
                       state         = %s,
                       date          = CURDATE(),
                       time          = CURTIME(),
                       id_user       = %s
                 WHERE code = %s
                """,
                (
                    data.get("firstName"),
                    data.get("lastName"),
                    data.get("email"),
                    data.get("idGender"),
                    data.get("idBloodType"),
                    data.get("birthDate"),
                    data.get("img", ""),
                    data.get("city", 0),
                    data.get("state", 0),
                    user_id,
                    data.get("code"),   # WHERE code = %s
                ),
            )
            conn.commit()
    finally:
        conn.close()

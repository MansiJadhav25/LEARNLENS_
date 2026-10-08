from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

import mysql.connector
import os
import uuid


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# CORS
# ============================================================

CORS(
    app,
    resources={
        r"/*": {
            "origins": "*"
        }
    }
)


# ============================================================
# UPLOAD FOLDER
# ============================================================

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(__file__),
    "uploads",
    "notes"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="learnlens"
    )


# ============================================================
# HOME / TEST ROUTE
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "message": "LearnLens Flask Backend is running successfully."
    })


# ============================================================
# STUDENT PROFILE
# ============================================================

@app.route("/student/<roll_number>")
def get_student(roll_number):

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        query = """
            SELECT
                s.student_id,
                s.student_name,
                s.roll_number,
                s.email,
                COALESCE(
                    AVG(m.marks_obtained),
                    0
                ) AS average_marks
            FROM students s

            LEFT JOIN marks m
                ON s.student_id = m.student_id

            WHERE s.roll_number = %s

            GROUP BY
                s.student_id,
                s.student_name,
                s.roll_number,
                s.email
        """

        cursor.execute(
            query,
            (roll_number,)
        )

        student = cursor.fetchone()

        cursor.close()
        db.close()


        # ----------------------------------------------------
        # STUDENT NOT FOUND
        # ----------------------------------------------------

        if not student:

            return jsonify({
                "message": "Student not found."
            }), 404


        # ----------------------------------------------------
        # CALCULATE AVERAGE
        # ----------------------------------------------------

        average = float(
            student["average_marks"]
        )


        # ----------------------------------------------------
        # FIND LEARNER CATEGORY
        # ----------------------------------------------------

        if average >= 80:

            category = "Advanced Learner"

        elif average >= 50:

            category = "Moderate Learner"

        else:

            category = "Slow Learner"


        student["average_marks"] = average
        student["category"] = category


        return jsonify(student)


    except mysql.connector.Error as error:

        return jsonify({
            "error": str(error)
        }), 500


    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# STUDENT RECOMMENDATIONS
# ============================================================

@app.route("/student/<roll_number>/recommendations")
def get_recommendations(roll_number):

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)


        # ====================================================
        # FIND STUDENT
        # ====================================================

        student_query = """

            SELECT
                s.student_id,
                s.student_name,
                s.roll_number,
                s.email,

                COALESCE(
                    AVG(m.marks_obtained),
                    0
                ) AS average_marks

            FROM students s

            LEFT JOIN marks m
                ON s.student_id = m.student_id

            WHERE s.roll_number = %s

            GROUP BY
                s.student_id,
                s.student_name,
                s.roll_number,
                s.email

        """

        cursor.execute(
            student_query,
            (roll_number,)
        )

        student = cursor.fetchone()


        # ====================================================
        # STUDENT NOT FOUND
        # ====================================================

        if not student:

            cursor.close()
            db.close()

            return jsonify({
                "message": "Student not found."
            }), 404


        # ====================================================
        # CALCULATE AVERAGE
        # ====================================================

        average = float(
            student["average_marks"]
        )


        # ====================================================
        # FIND LEARNER CATEGORY
        # ====================================================

        if average >= 80:

            category_name = "Advanced Learner"

        elif average >= 50:

            category_name = "Moderate Learner"

        else:

            category_name = "Slow Learner"


        # ====================================================
        # FIND WEAKEST SUBJECT
        # ====================================================

        weakest_subject_query = """

            SELECT
                s.subject_id,
                s.subject_name,
                AVG(m.marks_obtained) AS subject_marks

            FROM marks m

            JOIN subjects s
                ON m.subject_id = s.subject_id

            WHERE m.student_id = %s

            GROUP BY
                s.subject_id,
                s.subject_name

            ORDER BY subject_marks ASC

            LIMIT 1

        """

        cursor.execute(
            weakest_subject_query,
            (student["student_id"],)
        )

        weakest_subject = cursor.fetchone()


        # ====================================================
        # NO MARKS AVAILABLE
        # ====================================================

        if not weakest_subject:

            cursor.close()
            db.close()

            return jsonify({

                "student_name":
                    student["student_name"],

                "roll_number":
                    student["roll_number"],

                "average_marks":
                    average,

                "category":
                    category_name,

                "weakest_subject":
                    None,

                "weakest_marks":
                    None,

                "recommendations":
                    []

            })


        # ====================================================
        # WEAKEST SUBJECT DETAILS
        # ====================================================

        weakest_subject_id = (
            weakest_subject["subject_id"]
        )

        weakest_subject_name = (
            weakest_subject["subject_name"]
        )

        weakest_marks = float(
            weakest_subject["subject_marks"]
        )


        # ====================================================
        # FIND CATEGORY ID
        # ====================================================

        category_query = """

            SELECT
                category_id

            FROM learner_categories

            WHERE category_name = %s

        """

        cursor.execute(
            category_query,
            (category_name,)
        )

        category = cursor.fetchone()


        if not category:

            cursor.close()
            db.close()

            return jsonify({
                "message":
                    "Learner category not found."
            }), 404


        category_id = category["category_id"]


        # ====================================================
        # FIND RECOMMENDED TOPICS
        # ====================================================

        recommendation_query = """

            SELECT

                s.subject_name,

                lt.topic_id,

                lt.topic_name

            FROM category_topic_recommendations ctr

            JOIN learning_topics lt

                ON ctr.topic_id = lt.topic_id

            JOIN subjects s

                ON lt.subject_id = s.subject_id

            WHERE ctr.category_id = %s

              AND s.subject_id = %s

            ORDER BY lt.topic_id

        """

        cursor.execute(
            recommendation_query,
            (
                category_id,
                weakest_subject_id
            )
        )

        recommendations = cursor.fetchall()


        # ====================================================
        # FIND VIDEOS AND NOTES
        # ====================================================

        for recommendation in recommendations:

            topic_id = (
                recommendation["topic_id"]
            )


            # ------------------------------------------------
            # VIDEOS
            # ------------------------------------------------

            video_query = """

                SELECT

                    video_id,

                    video_title,

                    youtube_url

                FROM topic_videos

                WHERE topic_id = %s

                ORDER BY video_id

            """

            cursor.execute(
                video_query,
                (topic_id,)
            )

            recommendation["videos"] = (
                cursor.fetchall()
            )


            # ------------------------------------------------
            # NOTES
            # ------------------------------------------------

            notes_query = """

                SELECT

                    note_id,

                    notes_title,

                    notes_file_name,

                    notes_file_url

                FROM category_topic_notes

                WHERE category_id = %s

                  AND subject_id = %s

                  AND topic_id = %s

                ORDER BY note_id DESC

                LIMIT 1

            """

            cursor.execute(
                notes_query,
                (
                    category_id,
                    weakest_subject_id,
                    topic_id
                )
            )

            note = cursor.fetchone()


            if note:

                recommendation["notes"] = note

            else:

                recommendation["notes"] = None


        # ====================================================
        # CLOSE DATABASE
        # ====================================================

        cursor.close()
        db.close()


        # ====================================================
        # FINAL RESPONSE
        # ====================================================

        return jsonify({

            "student_name":
                student["student_name"],

            "roll_number":
                student["roll_number"],

            "average_marks":
                average,

            "category":
                category_name,

            "weakest_subject":
                weakest_subject_name,

            "weakest_marks":
                weakest_marks,

            "recommendations":
                recommendations

        })


    except mysql.connector.Error as error:

        return jsonify({
            "error": str(error)
        }), 500


    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# TEACHER RECOMMENDATION OPTIONS
# ============================================================

@app.route("/teacher/recommendation-options")
def get_recommendation_options():

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)


        # ====================================================
        # CATEGORIES
        # ====================================================

        cursor.execute("""

            SELECT
                category_id,
                category_name

            FROM learner_categories

            ORDER BY category_id

        """)

        categories = cursor.fetchall()


        # ====================================================
        # SUBJECTS
        # ====================================================

        cursor.execute("""

            SELECT
                subject_id,
                subject_name

            FROM subjects

            ORDER BY subject_id

        """)

        subjects = cursor.fetchall()


        # ====================================================
        # TOPICS
        # ====================================================

        cursor.execute("""

            SELECT
                topic_id,
                subject_id,
                topic_name

            FROM learning_topics

            ORDER BY
                subject_id,
                topic_id

        """)

        topics = cursor.fetchall()


        cursor.close()
        db.close()


        return jsonify({

            "categories":
                categories,

            "subjects":
                subjects,

            "topics":
                topics

        })


    except mysql.connector.Error as error:

        return jsonify({
            "error": str(error)
        }), 500


    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# TEACHER SAVE RECOMMENDATIONS
# ============================================================

@app.route(
    "/teacher/recommendations",
    methods=["POST"]
)
def save_teacher_recommendations():

    try:

        data = request.get_json()


        if not data:

            return jsonify({
                "message":
                    "No data received."
            }), 400


        category_id = data.get(
            "category_id"
        )

        subject_id = data.get(
            "subject_id"
        )

        topic_ids = data.get(
            "topic_ids"
        )


        # ====================================================
        # VALIDATION
        # ====================================================

        if not category_id:

            return jsonify({
                "message":
                    "Learner category is required."
            }), 400


        if not subject_id:

            return jsonify({
                "message":
                    "Subject is required."
            }), 400


        if not topic_ids:

            return jsonify({
                "message":
                    "Please select exactly 3 topics."
            }), 400


        if len(topic_ids) != 3:

            return jsonify({
                "message":
                    "Please select exactly 3 topics."
            }), 400


        # ====================================================
        # CHECK DUPLICATE TOPICS
        # ====================================================

        if len(set(topic_ids)) != 3:

            return jsonify({
                "message":
                    "Please select 3 different topics."
            }), 400


        db = get_db_connection()
        cursor = db.cursor()


        # ====================================================
        # VERIFY TOPICS BELONG TO SUBJECT
        # ====================================================

        for topic_id in topic_ids:

            cursor.execute("""

                SELECT topic_id

                FROM learning_topics

                WHERE topic_id = %s

                  AND subject_id = %s

            """, (
                topic_id,
                subject_id
            ))

            topic = cursor.fetchone()


            if not topic:

                cursor.close()
                db.close()

                return jsonify({
                    "message":
                        "One or more selected topics do not belong to the selected subject."
                }), 400


        # ====================================================
        # REMOVE OLD ASSIGNMENTS
        # ====================================================

        delete_query = """

            DELETE FROM
                category_topic_recommendations

            WHERE category_id = %s

              AND topic_id IN (

                    SELECT topic_id

                    FROM learning_topics

                    WHERE subject_id = %s

              )

        """

        cursor.execute(
            delete_query,
            (
                category_id,
                subject_id
            )
        )


        # ====================================================
        # INSERT NEW ASSIGNMENTS
        # ====================================================

        insert_query = """

            INSERT INTO
                category_topic_recommendations
                (
                    category_id,
                    topic_id
                )

            VALUES
                (%s, %s)

        """


        for topic_id in topic_ids:

            cursor.execute(
                insert_query,
                (
                    category_id,
                    topic_id
                )
            )


        db.commit()


        cursor.close()
        db.close()


        return jsonify({

            "message":
                "Recommendations assigned successfully.",

            "category_id":
                category_id,

            "subject_id":
                subject_id,

            "topic_ids":
                topic_ids

        })


    except mysql.connector.Error as error:

        return jsonify({
            "error": str(error)
        }), 500


    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# TEACHER UPLOAD NOTES
# ============================================================

@app.route(
    "/teacher/notes",
    methods=["POST"]
)
def save_teacher_notes():

    try:

        category_id = request.form.get(
            "category_id"
        )

        subject_id = request.form.get(
            "subject_id"
        )

        topic_id = request.form.get(
            "topic_id"
        )

        notes_title = request.form.get(
            "notes_title"
        )

        notes_file = request.files.get(
            "notes_file"
        )


        # ====================================================
        # VALIDATION
        # ====================================================

        if not category_id:

            return jsonify({
                "message":
                    "Learner category is required."
            }), 400


        if not subject_id:

            return jsonify({
                "message":
                    "Subject is required."
            }), 400


        if not topic_id:

            return jsonify({
                "message":
                    "Topic is required."
            }), 400


        if not notes_title:

            return jsonify({
                "message":
                    "Notes title is required."
            }), 400


        if not notes_file:

            return jsonify({
                "message":
                    "Please select a PDF file."
            }), 400


        # ====================================================
        # CHECK PDF
        # ====================================================

        original_filename = secure_filename(
            notes_file.filename
        )


        if not original_filename:

            return jsonify({
                "message":
                    "Invalid file name."
            }), 400


        if not original_filename.lower().endswith(
            ".pdf"
        ):

            return jsonify({
                "message":
                    "Only PDF files are allowed."
            }), 400


        db = get_db_connection()
        cursor = db.cursor(dictionary=True)


        # ====================================================
        # CHECK TOPIC
        # ====================================================

        cursor.execute("""

            SELECT
                topic_id

            FROM learning_topics

            WHERE topic_id = %s

              AND subject_id = %s

        """, (
            topic_id,
            subject_id
        ))


        topic = cursor.fetchone()


        if not topic:

            cursor.close()
            db.close()

            return jsonify({
                "message":
                    "Selected topic does not belong to this subject."
            }), 400


        # ====================================================
        # CREATE UNIQUE FILE NAME
        # ====================================================

        unique_filename = (
            str(uuid.uuid4())
            + "_"
            + original_filename
        )


        file_path = os.path.join(

            app.config["UPLOAD_FOLDER"],

            unique_filename

        )


        # ====================================================
        # SAVE FILE
        # ====================================================

        notes_file.save(
            file_path
        )


        # ====================================================
        # FILE URL
        # ====================================================

        notes_file_url = (
            "/uploads/notes/"
            + unique_filename
        )


        # ====================================================
        # REMOVE OLD NOTE
        # ====================================================

        cursor.execute("""

            DELETE FROM
                category_topic_notes

            WHERE category_id = %s

              AND topic_id = %s

        """, (
            category_id,
            topic_id
        ))


        # ====================================================
        # INSERT NEW NOTE
        # ====================================================

        cursor.execute("""

            INSERT INTO
                category_topic_notes
                (
                    category_id,
                    subject_id,
                    topic_id,
                    notes_title,
                    notes_file_name,
                    notes_file_url
                )

            VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

        """, (

            category_id,

            subject_id,

            topic_id,

            notes_title,

            original_filename,

            notes_file_url

        ))


        db.commit()


        cursor.close()
        db.close()


        return jsonify({

            "message":
                "Notes saved successfully.",

            "notes_title":
                notes_title,

            "notes_file_name":
                original_filename,

            "notes_file_url":
                notes_file_url

        })


    except mysql.connector.Error as error:

        return jsonify({
            "error": str(error)
        }), 500


    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


# ============================================================
# SERVE UPLOADED NOTES
# ============================================================

@app.route(
    "/uploads/notes/<path:filename>"
)
def serve_notes(filename):

    return send_from_directory(

        app.config["UPLOAD_FOLDER"],

        filename

    )


# ============================================================
# RUN FLASK
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
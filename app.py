from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import datetime
from collections import defaultdict
from flask import make_response
from weasyprint import HTML



app = Flask(__name__)
app.secret_key = 'MANUP'

def get_db_connection():
    conn = sqlite3.connect('Manup.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        client_name = request.form.get('client_name')
        client_address = request.form.get('client_address')
        client_phone_number = request.form.get('client_phone_number')
        client_email = request.form.get('client_email')

        if not all ([client_name, client_address, client_phone_number, client_email]):
            flash('All fields are required.', 'error')
            return render_template('add_client.html',
                client_name=client_name,
                client_address=client_address,
                client_phone_number=client_phone_number,
                client_email=client_email
            )


        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO clients (client_name, client_address, client_phone_number, client_email) VALUES (?, ?, ?, ?)',
                    (client_name, client_address, client_phone_number, client_email))
        
        conn.commit()
        conn.close()

        flash('New client added successfully.')
        return redirect(url_for('add_client'))
    else:
        return render_template('add_client.html')
    
@app.route('/client_list')
def client_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM clients')
    client_data = cur.fetchall()
    print(client_data)  # This will print the data in the console
    conn.close()
    return render_template('clients.html', clients=client_data)

@app.route('/edit_client_entry/<int:id>', methods=['GET'])
def edit_client_entry(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM clients WHERE id = ?', (id,))
    entry = cur.fetchone()
    conn.close()

    if entry:
        return render_template('edit_client_entry.html', entry=entry)
    else:
        flash('Client entry not found', 'error')
    return redirect(url_for('clients'))

@app.route('/update_client_entry/<int:id>', methods=['POST'])
def update_client_entry(id):
    client_name = request.form['client_name']
    client_address = request.form['client_address']
    client_phone_number = request.form['client_phone_number']
    client_email = request.form['client_email']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
                UPDATE clients SET client_name = ?, client_address = ?, client_phone_number = ?, client_email = ? WHERE id = ?''',
                (client_name, client_address, client_phone_number, client_email, id))
    conn.commit()
    conn.close()
    return redirect(url_for('client_list'))

@app.route('/delete_client_entry/<int:id>', methods=['POST'])
def delete_client_entry(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM clients WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Client entry deleted successfully!')
    return redirect(url_for('client_list'))


@app.route('/create_bid')
def create_bid():
    return render_template('create_bid.html') 

@app.route('/view_bid/<int:bid_id>')
def view_bid(bid_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM bids WHERE bid_id = ?', (bid_id,))
    bid_info = cur.fetchone()

    if not bid_info:
        conn.close()
        flash('Bid not found', 'error')
        return redirect(url_for('view_bids'))
    
    cur.execute('SELECT * FROM bid_items WHERE bid_id = ?', (bid_id,))
    bid_items = cur.fetchall()

    cur.execute('SELECT * FROM labor_items WHERE bid_id = ?', (bid_id,))
    labor_items = cur.fetchall()

    conn.close()

    bid_info = dict(bid_info) if bid_info else None
    bid_items = [dict(item) for item in bid_items] if bid_items else []
    labor_items = [dict(item) for item in labor_items] if labor_items else []

    return render_template('view_bid.html', bid_id=bid_id, bid=bid_info, bid_items=bid_items, labor_items=labor_items)



@app.route('/submit_estimate', methods=['POST'])
def submit_estimate():
    
    conn = get_db_connection()
    cur = conn.cursor()

    try:

        app.logger.debug(f"Form data: {request.form}")
        date = request.form['date']
        estimate_number = request.form['estimate_number']
        prepared_by = request.form['prepared_by']
        customer = request.form['customer']
        address = request.form['address']
        email = request.form['email']
        phone = request.form['phone']
        projected_start_date = request.form['projected_start_date']
        projected_end_date = request.form['projected_end_date']
        estimated_hours_days = request.form['estimated_hours_days']
        notes = request.form['notes']
        material_total = request.form.get('material_total', 0)
        labor_total = request.form.get('labor_total', 0)
        other = request.form.get('other', 0)
        grand_total = request.form.get('grand_total', 0)
        app.logger.debug(f"Inserting bid with estimate_number: {estimate_number}, prepared_by: {prepared_by}")
        cur.execute('INSERT INTO bids (date, estimate_number, prepared_by, customer, address, email, phone, projected_start_date, projected_end_date, estimated_hours_days, notes, material_total, labor_total, other, grand_total) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (date, estimate_number, prepared_by, customer, address, email, phone, projected_start_date, projected_end_date, estimated_hours_days, notes, material_total, labor_total, other, grand_total))
        bid_id = cur.lastrowid

    # Process bid items
        descriptions = request.form.getlist('description[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')
        amounts = request.form.getlist('amount[]')

        for description, quantity, price, amount in zip(descriptions, quantities, prices, amounts):
            cur.execute('INSERT INTO bid_items (bid_id, description, quantity, price, amount) VALUES (?, ?, ?, ?, ?)',
                        (bid_id, description, quantity, price, amount))
        
        tasks = request.form.getlist('task[]')
        labor_prices = request.form.getlist('labor_price[]')
        hours = request.form.getlist('hours')
        labor_totals = request.form.getlist('labor_total[]')

        app.logger.debug(f"Tasks: {tasks}")
        app.logger.debug(f"Labor Prices: {labor_prices}")
        app.logger.debug(f"Hours: {hours}")
        app.logger.debug(f"Labor Totals: {labor_totals}")


        for task, labor_price, hours, labor_total in zip(tasks, labor_prices, hours, labor_totals):
            cur.execute('INSERT INTO labor_items (bid_id, task, labor_price, hours, labor_total) VALUES (?, ?, ?, ?, ?)',
                        (bid_id, task, labor_price, hours, labor_total))
    
    # Move the conn.close() outside of the loop to close the connection after all items are inserted.
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f'Error submitting bid: {e}', 'error')
    finally:
        conn.close()

    flash('Bid submitted successfully!')
    return redirect(url_for('view_bids'))


@app.route('/view_bids')
def view_bids():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM bids')  # Adjust SQL query as needed
    bids = cur.fetchall()
    conn.close()
    return render_template('view_bids.html', bids=bids)

@app.route('/delete_bid/<int:bid_id>', methods=['POST'])
def delete_bid(bid_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM bids WHERE bid_id = ?', (bid_id,))
    conn.commit()
    conn.close()

    flash('Bid deleted successfully!')
    return redirect(url_for('view_bids'))

@app.route('/add_job', methods=['GET', 'POST'])
@app.route('/add/<int:job_id>', methods=['GET', 'POST'])
def add_job(job_id=None):
    job = None
    type_ids = []
    if  job_id:

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id))
        job = cur.fetchone()
        conn.close()
        if not job:
            return "Job not found", 404
        job = dict(job)

    if request.method == 'POST':
        job_name = request.form['job_name']
        address = request.form['address']
        price = request.form['price']
        projected_start_date = request.form['projected_start_date']
        projected_end_date = request.form['projected_end_date']
        type_id = request.form['type_id']
        customer_name = request.form['customer_name']
        customer_phone_number = request.form['customer_phone_number']
        customer_address = request.form['customer_address']
        email = request.form['email']
        job_details = request.form['job_details']
        status = request.form['status']
        type_ids = request.form.getlist('type_id')
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        workflow_type = request.form.get("workflow_type")

        conn = get_db_connection()
        cur = conn.cursor()


    for type_id in type_ids:
        cur.execute('INSERT INTO jobs (job_name, address, price, projected_start_date, projected_end_date, type_id, customer_name, customer_phone_number, customer_address, email, job_details, status, date, workflow_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (job_name, address, price, projected_start_date, projected_end_date, type_id, customer_name, customer_phone_number, customer_address, email, job_details, status, date, workflow_type))

        conn.commit()
        conn.close()

        return redirect(url_for('view_jobs'))

    else:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT type_id, type_name FROM job_types')
        job_types = cur.fetchall()
        conn.close()


    return render_template('add_job.html', job_types=job_types)
    
@app.route('/view_jobs')
def view_jobs():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM jobs')
    jobs = [dict(row) for row in cur.fetchall()]

    cur.execute('SELECT type_id, type_name FROM job_types')
    job_types = cur.fetchall()

    conn.close()
    return render_template('view_jobs.html', jobs=jobs, job_types=job_types)

@app.route('/add_instructions', methods=['POST'])
def add_instructions():
    if request.method == 'POST':
        type_id = request.form['type_id']
        instructions = request.form['instructions']

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('SELECT * FROM job_instructions WHERE type_id = ?', (type_id,))
        existing_instructions = cur.fetchone()

        if existing_instructions:
            cur.execute('UPDATE job_instructions SET instructions = ? WHERE type_id = ?', (instructions, type_id))
        else:
            cur.execute('INSERT INTO job_instructions (type_id, instructions) VALUES (?, ?)', (type_id, instructions))

            conn.commit()
            conn.close()

            return redirect(url_for('job_info', job_id=type_id))
    else:
        return "Method not allowed", 405
    

@app.route('/job/<int:job_id>')
def job_details(job_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()


    cur.execute('''
        SELECT j.*, jt.type_name FROM jobs j
        LEFT JOIN job_types jt ON j.type_id = jt.type_id
        WHERE j.job_id = ?''', (job_id,))
    
    
    job = cur.fetchone()
    if job is None:
        return "Job not found", 404 
    
    if isinstance(job['price'], float):
        job_price = job['price']

    else:
        job_price = str(job['price']).replace('$', '').replace(',', '')
    if '?' in str(job_price):
        job_price = 0.0
    else:
        job_price = float(job_price)

    job_dict = dict(job)
    job_dict['price'] = job_price

    cur.execute('SELECT * FROM job_types WHERE type_id = ?', (job['type_id'],))
    type_id = cur.fetchall()
    cur.execute('SELECT tool_name FROM job_tools WHERE type_id = ?', (job['type_id'],))
    tools = cur.fetchall()

    cur.execute('SELECT * FROM job_instructions WHERE type_id = ?', (job['type_id'],))
    instructions = cur.fetchall()

    instructions_text = None
    if instructions:
        instructions_text = instructions[0]['instructions']

    conn.close()
    return render_template('job_details.html', job=job_dict, tools=tools, instructions=instructions_text, job_types=type_id)

@app.route('/edit/<int:job_id>', methods=['GET'])
def edit_job(job_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
    job = cur.fetchone()

    if job is None:
        conn.close()
        return "Job not found", 404
    
    cur.execute('SELECT type_id, type_name FROM job_types')
    job_types = cur.fetchall()
    conn.close()

    return render_template('edit_job.html', job=job, job_types=job_types)

@app.route('/delete_job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM jobs WHERE job_id = ?', (job_id,))
    conn.commit()
    conn.close()

    flash('Job deleted successfully!')
    return redirect(url_for('view_jobs'))

@app.route('/update/<int:job_id>', methods=['POST'])
def update_job(job_id):
    job_name = request.form['job_name']
    address = request.form['address']
    price = request.form['price']
    projected_start_date = request.form['projected_start_date']
    projected_end_date = request.form['projected_end_date']
    type_id = request.form['type_id']
    customer_name = request.form['customer_name']
    customer_phone_number = request.form['customer_phone_number']
    customer_address = request.form['customer_address']
    email = request.form['email']
    job_details = request.form['job_details']
    status = request.form['status']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
                UPDATE jobs SET job_name = ?, address = ?, price = ?, projected_start_date = ?, projected_end_date = ?, type_id = ?, customer_name = ?, customer_phone_number = ?, customer_address = ?, email = ?, job_details = ?, status = ? WHERE job_id = ?''',
                (job_name, address, price, projected_start_date, projected_end_date, type_id, customer_name, customer_phone_number, customer_address, email, job_details, status, job_id))
    conn.commit()
    conn.close()
    

    return redirect(url_for('view_jobs'))

@app.route('/job/<int:job_id>/complete', methods=['POST'])
def mark_job_as_complete(job_id):
    try:
        print(f"Marking job {job_id} as complete...")

        conn = get_db_connection()
        cur = conn.cursor()

        # Update the status to 'Completed'
        cur.execute('UPDATE jobs SET status = "Completed" WHERE job_id = ?', (job_id,))
        update_result = cur.rowcount
        print(f"Updated {update_result} rows to status 'Completed'")

        # Fetch the job details
        cur.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
        job_data = cur.fetchone()

        if job_data:
        # Insert into completed_jobs table
            cur.execute('''INSERT INTO completed_jobs (job_id, job_name, address, price, projected_start_date, projected_end_date, type_id, status, customer_name, 
                    customer_phone_number, customer_address, email, job_details)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (job_data['job_id'], job_data['job_name'], job_data['address'], job_data['price'], job_data['projected_start_date'], job_data['projected_end_date'], job_data['type_id'],
                     job_data['status'], job_data['customer_name'], job_data['customer_phone_number'], 
                     job_data['customer_address'], job_data['email'], job_data['job_details']))

        # Delete FROM jobs table
            cur.execute('DELETE FROM jobs WHERE job_id = ?', (job_id,))
            delete_result = cur.rowcount
            print(f"Deleted {delete_result} rows FROM jobs")

        
            conn.commit()
            flash('Job marked as completed and moved to completed jobs.', 'success')
        else:
            flash('Job not found or already completed.', 'error')

        conn.close()
        return redirect(url_for('view_jobs'))
    except Exception as e:
        print(f"An error occurred: {e}")
        flash(f"An error occurred while marking job as complete: {e}", 'error')
        return redirect(url_for('view_jobs'))




@app.route('/completed_jobs')
def completed_jobs():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM completed_jobs')
    completed_jobs = [dict(row) for row in cur.fetchall()]

    for job in completed_jobs:
        if 'price' in job and job['price'] is not None:
            if isinstance(job['price'], str):
                price_str = job['price'].replace('$', '').replace(',', '')
            try:
                job['price'] = float(price_str)
            except ValueError:
                print(f"Could not covert price to float: {job['price']}")
                job['price'] = 0.0
            else:
                print(f"Price is already a float: {job['price']}")


    conn.close()

    
    return render_template('completed_jobs.html', jobs = completed_jobs)

@app.route('/download_bid_pdf/<int:bid_id>')
def download_bid_pdf(bid_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM bids WHERE bid_id = ?', (bid_id,))
    bid_info = cur.fetchone()

    if not bid_info:
        conn.close()
        flash('Bid not found', 'error')
        return redirect(url_for('view_bids'))
    
    cur.execute('SELECT * FROM bid_items WHERE bid_id = ?', (bid_id,))
    bid_items = cur.fetchall()

    cur.execute('SELECT * FROM labor_items WHERE bid_id = ?', (bid_id,))
    labor_items = cur.fetchall()

    conn.close()

    html_content = render_template('bid_pdf_template.html', bid=bid_info, bid_items=bid_items, labor_items=labor_items)
    pdf = HTML(string=html_content).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=bid_{bid_id}.pdf'
    return response

@app.route('/download_job_pdf/<int:job_id>')
def download_job_pdf(job_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch job information
    cur.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
    job_info = cur.fetchone()
    
    if not job_info:
        conn.close()
        flash('Job not found', 'error')
        return redirect(url_for('view_jobs'))
    
    # Fetch job types
    cur.execute('SELECT * FROM job_types')
    job_types = cur.fetchall()

    # Fetch tools for the job based on type_id
    cur.execute('SELECT tool_name FROM job_tools WHERE type_id = ?', (job_info['type_id'],))
    tools = cur.fetchall()

    # Fetch instructions for the job based on type_id
    cur.execute('SELECT instructions FROM job_instructions WHERE type_id = ?', (job_info['type_id'],))
    instructions = cur.fetchone()

    conn.close()

    # Convert to the appropriate data structures for template rendering
    job_info = dict(job_info)
    job_types = [dict(row) for row in job_types]
    tools = [dict(row) for row in tools]
    instructions = instructions['instructions'] if instructions else None

    # Render the HTML template
    html_content = render_template('job_pdf_template.html', job=job_info, job_types=job_types, tools=tools, instructions=instructions)
    pdf = HTML(string=html_content).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=job_{job_id}.pdf'
    return response

@app.route("/job/<int:job_id>/walkthrough")
def walkthrough_entry(job_id):
    conn = get_db_connection()

    walkthrough = conn.execute(
        "SELECT walkthrough_id FROM walkthroughs WHERE job_id = ?",
        (job_id,)
    ).fetchone()

    if walkthrough is None:
        conn.execute(
            "INSERT INTO walkthroughs (job_id) VALUES (?)",
            (job_id,)
        )
        conn.commit()

    conn.close()
    return redirect(url_for("walkthrough_add_findings", job_id=job_id))

@app.route("/job/<int:job_id>/walkthrough/add", methods=["GET", "POST"])
def walkthrough_add_findings(job_id):
    conn = get_db_connection()

    # 1️⃣ Ensure walkthrough exists
    walkthrough = conn.execute(
        "SELECT walkthrough_id FROM walkthroughs WHERE job_id = ?",
        (job_id,)
    ).fetchone()

    if not walkthrough:
        conn.execute(
            "INSERT INTO walkthroughs (job_id) VALUES (?)",
            (job_id,)
        )
        conn.commit()

        walkthrough = conn.execute(
            "SELECT walkthrough_id FROM walkthroughs WHERE job_id = ?",
            (job_id,)
        ).fetchone()

    walkthrough_id = walkthrough["walkthrough_id"]

    # 2️⃣ Handle POST actions
    if request.method == "POST":
        print("FORM DATA:", dict(request.form))
        action = request.form.get("action")

        # ➕ Add Area
        if action == "add_area":
            area_name = request.form.get("area_name")

            if area_name:
                conn.execute(
                    """
                    INSERT INTO walkthrough_areas (walkthrough_id, name)
                    VALUES (?, ?)
                    """,
                    (walkthrough_id, area_name)
                )
                conn.commit()

        # ➕ Add Finding
        elif action == "add_finding":
            area_id = request.form.get("area_id")
            problem_text = request.form.get("problem_text")
            notes = request.form.get("notes")

            if area_id and problem_text:
                conn.execute(
                    """
                    INSERT INTO walkthrough_findings
                    (area_id, problem_text, notes)
                    VALUES (?, ?, ?)
                    """,
                    (area_id, problem_text, notes)
                )
                conn.commit()
            return redirect(request.url)

    # 3️⃣ Load areas + findings
    areas = conn.execute(
        """
        SELECT *
        FROM walkthrough_areas
        WHERE walkthrough_id = ?
        """,
        (walkthrough_id,)
    ).fetchall()

    findings = {}
    for area in areas:
        findings[area["area_id"]] = conn.execute(
            """
            SELECT *
            FROM walkthrough_findings
            WHERE area_id = ?
            """,
            (area["area_id"],)
        ).fetchall()

    job = conn.execute(
        "SELECT * FROM jobs WHERE job_id = ?",
        (job_id,)
    ).fetchone()

    conn.close()
    print("AREAS:", [dict(a) for a in areas])
    print("FINDINGS:", {k: [dict(f) for f in v] for k, v in findings.items()})

    return render_template(
        "walkthrough/add_findings.html",
        job=job,
        areas=areas,
        findings=findings
    )


@app.route("/job/<int:job_id>/walkthrough/review", methods=["GET", "POST"])
def walkthrough_review(job_id):
    conn = get_db_connection()

    walkthrough = conn.execute(
        "SELECT walkthrough_id FROM walkthroughs WHERE job_id = ?",
        (job_id,)
    ).fetchone()

    walkthrough_id = walkthrough["walkthrough_id"]

    if request.method == "POST":
        task_ids = request.form.getlist("task_ids[]")

        for task_id in task_ids:
            conn.execute("""
                UPDATE walkthrough_findings
                SET description = ?, status = ?
                WHERE finding_id = ?
            """, (
                request.form.get(f"description_{task_id}"),
                request.form.get(f"status_{task_id}"),
                task_id
            ))
        conn.commit()

    tasks = conn.execute("""
        SELECT f.*, a.name AS category_name
        FROM walkthrough_findings f
        JOIN walkthrough_areas a ON f.area_id = a.area_id
        WHERE a.walkthrough_id = ?
    """, (walkthrough_id,)).fetchall()

    job = conn.execute(
        "SELECT * FROM jobs WHERE job_id = ?",
        (job_id,)
    ).fetchone()

    conn.close()

    return render_template(
        "walkthrough/review.html",
        job=job,
        tasks=tasks
    )

@app.route("/job/<int:job_id>/walkthrough/report/pdf")
def walkthrough_report_pdf(job_id):
    conn = get_db_connection()

    job = conn.execute(
        "SELECT * FROM jobs WHERE job_id = ?",
        (job_id,)
    ).fetchone()

    areas = conn.execute("""
        SELECT *
        FROM walkthrough_areas
        WHERE walkthrough_id = (
            SELECT walkthrough_id FROM walkthroughs WHERE job_id = ?
        )
    """, (job_id,)).fetchall()

    problems = {}
    for area in areas:
        problems[area["area_id"]] = conn.execute("""
            SELECT f.*, i.filename
            FROM walkthrough_findings f
            LEFT JOIN finding_images i ON f.finding_id = i.finding_id
            WHERE f.area_id = ?
        """, (area["area_id"],)).fetchall()

    conn.close()

    html = render_template(
        "walkthrough/report_pdf.html",
        job=job,
        areas=areas,
        problems=problems
    )

    return HTML(string=html).write_pdf()

@app.route("/job/<int:job_id>/walkthrough/work-order/pdf")
def walkthrough_work_order_pdf(job_id):
    conn = get_db_connection()

    tasks = conn.execute("""
        SELECT f.*, a.name AS category_name
        FROM walkthrough_findings f
        JOIN walkthrough_areas a ON f.area_id = a.area_id
        WHERE a.walkthrough_id = (
            SELECT walkthrough_id FROM walkthroughs WHERE job_id = ?
        )
    """, (job_id,)).fetchall()

    job = conn.execute(
        "SELECT * FROM jobs WHERE job_id = ?",
        (job_id,)
    ).fetchone()

    conn.close()

    html = render_template(
        "walkthrough/work_order_pdf.html",
        job=job,
        tasks=tasks
    )

    return HTML(string=html).write_pdf()


if __name__ == '__main__':
    app.run(debug=True)
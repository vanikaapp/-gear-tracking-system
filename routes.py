from flask import render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from app import app, db
from models import Trailer, GearSnapshot, DriverAssignment, AuditLog

@app.route('/')
def index():
    """Dashboard with overview of system status"""
    trailer_count = Trailer.query.count()
    recent_audits = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(5).all()
    active_assignments = DriverAssignment.query.filter(DriverAssignment.returned_date.is_(None)).count()
    
    return render_template('index.html', 
                         trailer_count=trailer_count,
                         recent_audits=recent_audits,
                         active_assignments=active_assignments)

@app.route('/trailers')
def trailers():
    """List all trailers"""
    search = request.args.get('search', '')
    if search:
        trailers_list = Trailer.query.filter(
            Trailer.trailer_id.contains(search) | 
            Trailer.location.contains(search) |
            Trailer.status.contains(search)
        ).all()
    else:
        trailers_list = Trailer.query.all()
    
    return render_template('trailers.html', trailers=trailers_list, search=search)

@app.route('/trailers/add', methods=['GET', 'POST'])
def add_trailer():
    """Add a new trailer"""
    if request.method == 'POST':
        try:
            trailer_id = request.form.get('trailer_id', '').strip()
            location = request.form.get('location', '').strip()
            status = request.form.get('status', 'Available')
            notes = request.form.get('notes', '').strip()
            
            # Validate required fields
            if not trailer_id:
                flash('Trailer ID is required!', 'error')
                return render_template('add_trailer.html')
            
            # Check if trailer ID already exists
            existing = Trailer.query.filter_by(trailer_id=trailer_id).first()
            if existing:
                flash(f'Trailer {trailer_id} already exists!', 'error')
                return render_template('add_trailer.html')
            
            trailer = Trailer(
                trailer_id=trailer_id,
                location=location if location else None,
                status=status,
                notes=notes if notes else None
            )
            
            db.session.add(trailer)
            db.session.commit()
            app.logger.info(f"Trailer {trailer_id} added with ID {trailer.id}")
            
            # Create audit log
            audit = AuditLog(
                trailer_id=trailer.id,
                action_type='CREATE',
                description=f'Trailer {trailer_id} created with status {status}'
            )
            db.session.add(audit)
            db.session.commit()
            app.logger.info(f"Audit log created for trailer {trailer_id}")
            
            flash(f'Trailer {trailer_id} added successfully!', 'success')
            return redirect(url_for('trailers'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding trailer: {str(e)}")
            flash(f'Error adding trailer: {str(e)}', 'error')
            return render_template('add_trailer.html')
    
    return render_template('add_trailer.html')

@app.route('/gear-snapshots')
def gear_snapshots():
    """List all gear snapshots"""
    trailer_id = request.args.get('trailer_id')
    if trailer_id:
        snapshots = GearSnapshot.query.join(Trailer).filter(
            Trailer.trailer_id == trailer_id
        ).order_by(GearSnapshot.date_recorded.desc()).all()
    else:
        snapshots = GearSnapshot.query.join(Trailer).order_by(
            GearSnapshot.date_recorded.desc()
        ).all()
    
    trailers_list = Trailer.query.all()
    return render_template('gear_snapshots.html', snapshots=snapshots, 
                         trailers=trailers_list, selected_trailer=trailer_id)

@app.route('/gear-snapshots/add', methods=['GET', 'POST'])
def add_gear_snapshot():
    """Add a new gear snapshot"""
    if request.method == 'POST':
        trailer_id = request.form['trailer_id']
        gear_type = request.form['gear_type']
        quantity = int(request.form['quantity'])
        condition = request.form['condition']
        notes = request.form['notes']
        
        snapshot = GearSnapshot(
            trailer_id=trailer_id,
            gear_type=gear_type,
            quantity=quantity,
            condition=condition,
            notes=notes
        )
        
        db.session.add(snapshot)
        db.session.commit()
        
        # Create audit log
        trailer = Trailer.query.get(trailer_id)
        audit = AuditLog(
            trailer_id=trailer_id,
            action_type='ADD',
            gear_type=gear_type,
            quantity_change=quantity,
            new_condition=condition,
            description=f'Added {quantity} {gear_type}(s) in {condition} condition'
        )
        db.session.add(audit)
        db.session.commit()
        
        flash(f'Gear snapshot added for trailer {trailer.trailer_id}!', 'success')
        return redirect(url_for('gear_snapshots'))
    
    trailers_list = Trailer.query.all()
    return render_template('add_gear_snapshot.html', trailers=trailers_list)

@app.route('/driver-assignments')
def driver_assignments():
    """List all driver assignments"""
    assignments = DriverAssignment.query.join(Trailer).order_by(
        DriverAssignment.assigned_date.desc()
    ).all()
    
    return render_template('driver_assignments.html', assignments=assignments)

@app.route('/driver-assignments/add', methods=['GET', 'POST'])
def add_driver_assignment():
    """Add a new driver assignment"""
    if request.method == 'POST':
        trailer_id = request.form['trailer_id']
        driver_name = request.form['driver_name']
        notes = request.form['notes']
        
        # Check if trailer is already assigned to someone else
        existing = DriverAssignment.query.filter_by(
            trailer_id=trailer_id,
            returned_date=None
        ).first()
        
        if existing:
            trailer = Trailer.query.get(trailer_id)
            flash(f'Trailer {trailer.trailer_id} is already assigned to {existing.driver_name}!', 'error')
            return render_template('add_driver_assignment.html', trailers=Trailer.query.all())
        
        assignment = DriverAssignment(
            trailer_id=trailer_id,
            driver_name=driver_name,
            notes=notes
        )
        
        db.session.add(assignment)
        db.session.commit()
        
        # Create audit log
        trailer = Trailer.query.get(trailer_id)
        audit = AuditLog(
            trailer_id=trailer_id,
            action_type='ASSIGN',
            description=f'Trailer assigned to driver {driver_name}'
        )
        db.session.add(audit)
        db.session.commit()
        
        flash(f'Trailer {trailer.trailer_id} assigned to {driver_name}!', 'success')
        return redirect(url_for('driver_assignments'))
    
    trailers_list = Trailer.query.all()
    return render_template('add_driver_assignment.html', trailers=trailers_list)

@app.route('/driver-assignments/<int:assignment_id>/return', methods=['POST'])
def return_trailer(assignment_id):
    """Mark a trailer as returned"""
    assignment = DriverAssignment.query.get_or_404(assignment_id)
    assignment.returned_date = datetime.utcnow()
    
    db.session.commit()
    
    # Create audit log
    audit = AuditLog(
        trailer_id=assignment.trailer_id,
        action_type='RETURN',
        description=f'Trailer returned by driver {assignment.driver_name}'
    )
    db.session.add(audit)
    db.session.commit()
    
    flash(f'Trailer {assignment.trailer.trailer_id} marked as returned!', 'success')
    return redirect(url_for('driver_assignments'))

@app.route('/reports')
def reports():
    """Generate reports for gear and driver tracking"""
    trailer_id = request.args.get('trailer_id')
    
    trailer_gear = {}
    last_driver = {}
    
    if trailer_id:
        # Get gear for specific trailer
        trailer = Trailer.query.filter_by(trailer_id=trailer_id).first()
        if trailer:
            gear_data = GearSnapshot.query.filter_by(trailer_id=trailer.id).order_by(
                GearSnapshot.gear_type, GearSnapshot.date_recorded.desc()
            ).all()
            
            # Group by gear type and get latest snapshot
            gear_dict = {}
            for gear in gear_data:
                if gear.gear_type not in gear_dict:
                    gear_dict[gear.gear_type] = gear
            
            trailer_gear[trailer_id] = list(gear_dict.values())
            
            # Get last driver assignment
            last_assignment = DriverAssignment.query.filter_by(
                trailer_id=trailer.id
            ).order_by(DriverAssignment.assigned_date.desc()).first()
            
            if last_assignment:
                last_driver[trailer_id] = last_assignment
    else:
        # Get all trailers and their latest gear/driver info
        trailers_list = Trailer.query.all()
        for trailer in trailers_list:
            # Latest gear snapshots
            gear_data = GearSnapshot.query.filter_by(trailer_id=trailer.id).order_by(
                GearSnapshot.gear_type, GearSnapshot.date_recorded.desc()
            ).all()
            
            gear_dict = {}
            for gear in gear_data:
                if gear.gear_type not in gear_dict:
                    gear_dict[gear.gear_type] = gear
            
            if gear_dict:
                trailer_gear[trailer.trailer_id] = list(gear_dict.values())
            
            # Last driver assignment
            last_assignment = DriverAssignment.query.filter_by(
                trailer_id=trailer.id
            ).order_by(DriverAssignment.assigned_date.desc()).first()
            
            if last_assignment:
                last_driver[trailer.trailer_id] = last_assignment
    
    trailers_list = Trailer.query.all()
    return render_template('reports.html', 
                         trailer_gear=trailer_gear,
                         last_driver=last_driver,
                         trailers=trailers_list,
                         selected_trailer=trailer_id)

@app.route('/audit-log')
def audit_log():
    """View audit log for all trailers or specific trailer"""
    trailer_id = request.args.get('trailer_id')
    
    if trailer_id:
        trailer = Trailer.query.filter_by(trailer_id=trailer_id).first()
        if trailer:
            logs = AuditLog.query.filter_by(trailer_id=trailer.id).order_by(
                AuditLog.created_at.desc()
            ).all()
        else:
            logs = []
    else:
        logs = AuditLog.query.join(Trailer).order_by(
            AuditLog.created_at.desc()
        ).all()
    
    trailers_list = Trailer.query.all()
    return render_template('audit_log.html', 
                         logs=logs,
                         trailers=trailers_list,
                         selected_trailer=trailer_id)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html'), 500

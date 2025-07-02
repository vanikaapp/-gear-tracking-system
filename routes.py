from flask import render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import pytz
from app import app, db
from models import Trailer, GearSnapshot, DriverAssignment, AuditLog, get_est_now

# EST timezone
EST = pytz.timezone('US/Eastern')

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

@app.route('/trailers/<trailer_id>')
def trailer_detail(trailer_id):
    """Show detailed view of a specific trailer"""
    trailer = Trailer.query.filter_by(trailer_id=trailer_id).first_or_404()
    
    # Get current driver assignment
    current_driver = trailer.get_current_driver()
    
    # Get latest gear for each type
    latest_gear = trailer.get_latest_gear()
    
    # Get recent audit logs
    recent_logs = trailer.get_recent_logs(limit=20)
    
    # Get assignment history
    assignment_history = DriverAssignment.query.filter_by(
        trailer_id=trailer.id
    ).order_by(DriverAssignment.assigned_date.desc()).limit(10).all()
    
    return render_template('trailer_detail.html', 
                         trailer=trailer,
                         current_driver=current_driver,
                         latest_gear=latest_gear,
                         recent_logs=recent_logs,
                         assignment_history=assignment_history)

@app.route('/trailers/<trailer_id>/delete', methods=['POST'])
def delete_trailer(trailer_id):
    """Delete a trailer and all related data"""
    trailer = Trailer.query.filter_by(trailer_id=trailer_id).first_or_404()
    
    try:
        # Check if trailer has active assignments
        active_assignment = DriverAssignment.query.filter_by(
            trailer_id=trailer.id,
            returned_date=None
        ).first()
        
        if active_assignment:
            flash(f'Cannot delete trailer {trailer_id}: Currently assigned to {active_assignment.driver_name}. Please return the trailer first.', 'error')
            return redirect(url_for('trailer_detail', trailer_id=trailer_id))
        
        # Store trailer info for logging
        trailer_info = f"{trailer.trailer_id} (Location: {trailer.location or 'None'})"
        
        # Delete trailer (cascade will handle related records)
        db.session.delete(trailer)
        db.session.commit()
        
        app.logger.info(f"Trailer {trailer_info} deleted successfully")
        flash(f'Trailer {trailer.trailer_id} has been permanently deleted from the system.', 'success')
        return redirect(url_for('trailers'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting trailer {trailer_id}: {str(e)}")
        flash(f'Error deleting trailer: {str(e)}', 'error')
        return redirect(url_for('trailer_detail', trailer_id=trailer_id))

@app.route('/trailers/add', methods=['GET', 'POST'])
def add_trailer():
    """Add a new trailer"""
    app.logger.info(f"add_trailer called with method: {request.method}")
    
    if request.method == 'POST':
        try:
            app.logger.info("Processing POST request for add_trailer")
            
            trailer_id = request.form.get('trailer_id', '').strip()
            location = request.form.get('location', '').strip()
            status = request.form.get('status', 'Available')
            notes = request.form.get('notes', '').strip()
            
            app.logger.info(f"Form data - ID: {trailer_id}, Location: {location}, Status: {status}")
            
            # Validate required fields
            if not trailer_id:
                app.logger.warning("Trailer ID is missing")
                flash('Trailer ID is required!', 'error')
                return render_template('add_trailer.html')
            
            # Check if trailer ID already exists
            existing = Trailer.query.filter_by(trailer_id=trailer_id).first()
            if existing:
                app.logger.warning(f"Trailer {trailer_id} already exists")
                flash(f'Trailer {trailer_id} already exists!', 'error')
                return render_template('add_trailer.html')
            
            trailer = Trailer(
                trailer_id=trailer_id,
                location=location if location else None,
                status=status,
                notes=notes if notes else None
            )
            
            app.logger.info(f"Creating trailer object: {trailer}")
            
            db.session.add(trailer)
            db.session.commit()
            app.logger.info(f"Trailer {trailer_id} added successfully with ID {trailer.id}")
            
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
            app.logger.error(f"Error adding trailer: {str(e)}", exc_info=True)
            flash(f'Error adding trailer: {str(e)}', 'error')
            return render_template('add_trailer.html')
    
    app.logger.info("Rendering add_trailer.html template")
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
        
        # Create assignment
        assignment = DriverAssignment(
            trailer_id=trailer_id,
            driver_name=driver_name,
            notes=notes
        )
        
        # Update trailer status to "In Use"
        trailer = Trailer.query.get(trailer_id)
        old_status = trailer.status
        trailer.status = 'In Use'
        trailer.updated_at = get_est_now()
        
        db.session.add(assignment)
        db.session.commit()
        
        # Create audit log for assignment
        audit_assignment = AuditLog(
            trailer_id=trailer_id,
            action_type='ASSIGN',
            description=f'Trailer assigned to driver {driver_name}'
        )
        db.session.add(audit_assignment)
        
        # Create audit log for status change
        audit_status = AuditLog(
            trailer_id=trailer_id,
            action_type='UPDATE',
            description=f'Status changed from {old_status} to In Use (driver assigned)'
        )
        db.session.add(audit_status)
        db.session.commit()
        
        flash(f'Trailer {trailer.trailer_id} assigned to {driver_name} and status updated to "In Use"!', 'success')
        return redirect(url_for('driver_assignments'))
    
    # Only show available trailers for assignment
    trailers_list = Trailer.query.filter(Trailer.status.in_(['Available', 'Maintenance'])).all()
    return render_template('add_driver_assignment.html', trailers=trailers_list)

@app.route('/driver-assignments/<int:assignment_id>/return', methods=['POST'])
def return_trailer(assignment_id):
    """Mark a trailer as returned"""
    assignment = DriverAssignment.query.get_or_404(assignment_id)
    assignment.returned_date = get_est_now()
    
    # Update trailer status back to "Available"
    trailer = assignment.trailer
    old_status = trailer.status
    trailer.status = 'Available'
    trailer.updated_at = get_est_now()
    
    db.session.commit()
    
    # Create audit log for return
    audit_return = AuditLog(
        trailer_id=assignment.trailer_id,
        action_type='RETURN',
        description=f'Trailer returned by driver {assignment.driver_name}'
    )
    db.session.add(audit_return)
    
    # Create audit log for status change
    audit_status = AuditLog(
        trailer_id=assignment.trailer_id,
        action_type='UPDATE',
        description=f'Status changed from {old_status} to Available (trailer returned)'
    )
    db.session.add(audit_status)
    db.session.commit()
    
    flash(f'Trailer {assignment.trailer.trailer_id} returned and status updated to "Available"!', 'success')
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
        # Find trailer by trailer_id string (not database id)
        trailer = Trailer.query.filter_by(trailer_id=trailer_id).first()
        if trailer:
            # Filter logs by the trailer's database id
            logs = AuditLog.query.filter_by(trailer_id=trailer.id).order_by(
                AuditLog.created_at.desc()
            ).all()
        else:
            logs = []
            flash(f'Trailer {trailer_id} not found.', 'error')
    else:
        # Show all logs
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

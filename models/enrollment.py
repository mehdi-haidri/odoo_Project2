from odoo import models, fields, api


class EnrollmentExtension(models.Model):
    _name = 'elearning.enrollment'
    _description = 'Course Enrollment'
    
    # Basic fields
    course_id = fields.Many2one('elearning.course', string='Course', required=True, ondelete='cascade')
    student_id = fields.Many2one('res.partner', string='Student', required=True, ondelete='cascade')
    status = fields.Selection([
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='active')
    enrollment_date = fields.Date(string='Enrollment Date', default=fields.Date.today)
    progress = fields.Float(string='Progress (%)', default=0.0)
    completed_lesson_ids = fields.Many2many('elearning.lesson', string='Completed Lessons')
    
    # Certificate fields
    certificate_earned = fields.Boolean(string='Certificate Earned', default=False)
    certificate_date = fields.Date(string='Certificate Date')
    final_score = fields.Float(string='Final Score (%)')
    
    def mark_lesson_complete(self, lesson_id):
        """Mark lesson as complete and check certificate eligibility"""
        if lesson_id not in self.completed_lesson_ids.ids:
            self.write({'completed_lesson_ids': [(4, lesson_id)]})
            
        self._recompute_progress()
        return True
    
    def _recompute_progress(self):
        """Recalculate progress and update status"""
        # Force flush to ensure new lessons are visible to search
        self.env.flush_all()
        # Invalidate all caches to ensure we read fresh data from DB
        self.env.invalidate_all()
        
        for enrollment in self:
            # Use search instead of search_count to be absolutely sure
            published_lessons = self.env['elearning.lesson'].sudo().search([
                ('course_id', '=', enrollment.course_id.id),
                ('is_published', '=', True)
            ])
            total_lessons = len(published_lessons)
            
            # Filter completed lessons to ensure they are still published
            completed_published_count = 0
            for lesson in enrollment.completed_lesson_ids:
                if lesson.is_published:
                    completed_published_count += 1
            
            new_progress = 0.0
            if total_lessons > 0:
                new_progress = (completed_published_count / total_lessons) * 100.0
            else:
                new_progress = 100.0
            
            vals = {'progress': new_progress}
            
            # Check if certificate should be awarded
            if new_progress >= enrollment.course_id.require_completion_percentage:
                enrollment._create_certificate()
                if enrollment.status != 'completed':
                    vals['status'] = 'completed'
            
            # If new content was added (progress < 100) and it was completed, revert to active
            if new_progress < 100 and enrollment.status == 'completed':
                vals['status'] = 'active'
            
            # Write changes explicitly
            enrollment.write(vals)

    def _create_certificate(self):
        """Create certificate when course is completed"""
        if not self.certificate_earned:
            # Use sudo() to allow certificate creation even if user doesn't have create rights
            certificate_model = self.env['elearning.certificate'].sudo()
            certificate_model.create({
                'enrollment_id': self.id,
                'grade': self.final_score or self.progress,
            })
            self.certificate_earned = True
            self.certificate_date = fields.Date.today()

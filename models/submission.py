from odoo import models, fields, api

class Submission(models.Model):
    _name = 'elearning.submission'
    _description = 'Assignment Submission'
    _order = 'create_date desc'

    lesson_id = fields.Many2one('elearning.lesson', string='Lesson', required=True, ondelete='cascade')
    student_id = fields.Many2one('res.partner', string='Student', required=True, ondelete='cascade')
    
    submission_file = fields.Binary(string='Submission File', required=True)
    submission_filename = fields.Char(string='Filename')
    submission_text = fields.Html(string='Submission Notes')
    
    submitted_date = fields.Datetime(string='Submitted Date', default=fields.Datetime.now)
    
    # Grading
    grade = fields.Float(string='Grade')
    instructor_feedback = fields.Html(string='Instructor Feedback')
    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('graded', 'Graded')
    ], string='Status', default='submitted')

    @api.model
    def create(self, vals):
        submission = super(Submission, self).create(vals)
        # Send submission email to instructor
        template = self.env.ref('odoo_Project2.mail_template_assignment_submitted', raise_if_not_found=False)
        if template:
            template.send_mail(submission.id, force_send=True)
        return submission

    def action_grade_submission(self):
        """Mark submission as graded and update progress"""
        self.ensure_one()
        self.state = 'graded'
        
        # If grade is passing (e.g. > 50%), mark lesson as complete
        # You might want to make the passing score configurable on the lesson
        if self.grade >= 50:
            enrollment = self.env['elearning.enrollment'].search([
                ('course_id', '=', self.lesson_id.course_id.id),
                ('student_id', '=', self.student_id.id)
            ], limit=1)
            
            if enrollment:
                enrollment.mark_lesson_complete(self.lesson_id.id)
        
        # Send graded email to student
        template = self.env.ref('odoo_Project2.mail_template_assignment_graded', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

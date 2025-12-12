from odoo import models, fields, api


class CourseExtension(models.Model):
    _name = 'elearning.course'
    _description = 'Course'
    
    # Basic fields
    name = fields.Char(string='Course Name', required=True)
    description = fields.Text(string='Description')
    image = fields.Binary(string='Image')
    instructor_id = fields.Many2one('res.partner', string='Instructor')
    category_id = fields.Many2one('elearning.category', string='Category')
    
    # Course details
    level = fields.Selection([
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ], string='Level', default='beginner')
    price = fields.Float(string='Price')
    duration_hours = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    is_published = fields.Boolean(string='Published', default=False)
    
    # Relations
    lessons = fields.One2many('elearning.lesson', 'course_id', string='Lessons')
    enrollments = fields.One2many('elearning.enrollment', 'course_id', string='Enrollments')
    
    # Computed fields
    student_count = fields.Integer(string='Student Count', compute='_compute_student_count')
    
    # Certificate fields
    certificate_template = fields.Html(string='Certificate Template', help='HTML template for certificate')
    certificate_validity_days = fields.Integer(string='Certificate Valid Days', default=365)
    allow_certificate_download = fields.Boolean(string='Allow Certificate Download', default=True)
    require_completion_percentage = fields.Integer(
        string='Required Completion %', 
        default=80,
        help='Percentage of course content to complete before certificate'
    )
    difficulty_score = fields.Integer(string='Difficulty Score', default=50)
    
    @api.depends('lessons.duration_minutes')
    def _compute_duration(self):
        for course in self:
            total_minutes = sum(course.lessons.mapped('duration_minutes'))
            course.duration_hours = total_minutes / 60.0

    @api.depends('enrollments')
    def _compute_student_count(self):
        for course in self:
            course.student_count = len(course.enrollments)

    def write(self, vals):
        res = super(CourseExtension, self).write(vals)
        # If lessons or completion requirements change, recompute progress for all enrollments
        if 'lessons' in vals or 'require_completion_percentage' in vals:
            for course in self:
                enrollments = self.env['elearning.enrollment'].sudo().search([('course_id', '=', course.id)])
                if enrollments:
                    enrollments._recompute_progress()
        return res

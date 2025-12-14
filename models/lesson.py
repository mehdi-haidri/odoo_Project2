from odoo import models, fields, api


class Lesson(models.Model):
    _name = 'elearning.lesson'
    _description = 'Course Lesson'
    _order = 'sequence, id'

    name = fields.Char(string='Lesson Title', required=True)
    course_id = fields.Many2one('elearning.course', string='Course', required=True, ondelete='cascade')
    
    description = fields.Html(string='Description')
    content = fields.Html(string='Content')
    video_url = fields.Char(string='Video URL')
    video_embed_url = fields.Char(compute='_compute_video_embed_url', string='Embed URL')
    
    sequence = fields.Integer(string='Sequence', default=10)
    duration_minutes = fields.Integer(string='Duration (Minutes)')
    
    is_published = fields.Boolean(string='Published', default=False)
    is_preview = fields.Boolean(string='Preview Available', default=False, help="Allow anyone to view this lesson without enrollment")
    
    # Content Type
    lesson_type = fields.Selection([
        ('document', 'Document'),
        ('video', 'Video'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment')
    ], string='Lesson Type', default='document', required=True)
    
    # Document Content
    document_file = fields.Binary(string='Document File')
    document_filename = fields.Char(string='Document Filename')

    # Assignment Content
    assignment_instructions = fields.Html(string='Assignment Instructions')
    
    # Quiz/Assessment
    has_quiz = fields.Boolean(string='Has Quiz')
    quiz_passing_score = fields.Integer(string='Passing Score (%)', default=70)
    question_ids = fields.One2many('elearning.lesson.question', 'lesson_id', string='Questions')

    @api.depends('video_url')
    def _compute_video_embed_url(self):
        for lesson in self:
            if lesson.video_url:
                if 'youtube.com/watch?v=' in lesson.video_url:
                    video_id = lesson.video_url.split('v=')[1].split('&')[0]
                    lesson.video_embed_url = f'https://www.youtube.com/embed/{video_id}'
                elif 'youtu.be/' in lesson.video_url:
                    video_id = lesson.video_url.split('youtu.be/')[1].split('?')[0]
                    lesson.video_embed_url = f'https://www.youtube.com/embed/{video_id}'
                else:
                    lesson.video_embed_url = lesson.video_url
            else:
                lesson.video_embed_url = False

    @api.model
    def create(self, vals):
        lesson = super(Lesson, self).create(vals)
        if lesson.course_id:
            self.env.flush_all()
            lesson.course_id.invalidate_recordset(['lessons'])
            enrollments = self.env['elearning.enrollment'].sudo().search([('course_id', '=', lesson.course_id.id)])
            if enrollments:
                enrollments._recompute_progress()
        return lesson

    def write(self, vals):
        # Capture courses before write (in case course_id changes)
        courses = self.mapped('course_id')
        res = super(Lesson, self).write(vals)
        # Add new courses
        courses |= self.mapped('course_id')
        
        self.env.flush_all()
        
        for course in courses:
            course.invalidate_recordset(['lessons'])
            enrollments = self.env['elearning.enrollment'].sudo().search([('course_id', '=', course.id)])
            if enrollments:
                enrollments._recompute_progress()
        return res

    def unlink(self):
        courses = self.mapped('course_id')
        res = super(Lesson, self).unlink()
        
        self.env.flush_all()
        
        for course in courses:
            course.invalidate_recordset(['lessons'])
            enrollments = self.env['elearning.enrollment'].sudo().search([('course_id', '=', course.id)])
            if enrollments:
                enrollments._recompute_progress()
        return res


class LessonQuestion(models.Model):
    _name = 'elearning.lesson.question'
    _description = 'Lesson Question'
    _order = 'sequence, id'

    lesson_id = fields.Many2one('elearning.lesson', string='Lesson', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    question = fields.Char(string='Question', required=True)
    
    # Simple multiple choice or text
    question_type = fields.Selection([
        ('multiple_choice', 'Multiple Choice'),
        ('text', 'Text Input')
    ], string='Type', default='multiple_choice')
    
    # For multiple choice
    option_ids = fields.One2many('elearning.lesson.question.option', 'question_id', string='Options')
    
    # For text input
    correct_answer_text = fields.Char(string='Correct Answer Text')


class LessonQuestionOption(models.Model):
    _name = 'elearning.lesson.question.option'
    _description = 'Lesson Question Option'
    _order = 'sequence, id'

    question_id = fields.Many2one('elearning.lesson.question', string='Question', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    content = fields.Char(string='Option Content', required=True)
    is_correct = fields.Boolean(string='Is Correct')




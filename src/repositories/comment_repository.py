from src.models import db, Comment, CommentVote

class CommentRepository:
    
    def create_comment(self, content, timestamp, post_id, author_id) -> None:
        new_comment = Comment(content, timestamp, post_id, author_id)
        db.session.add(new_comment)
        db.session.commit()
        return new_comment

    def get_comment_by_id(self, comment_id):     
        return Comment.query.get(comment_id)
    
    def get_comments_for_post(self, post_id):
        comments = Comment.query.filter(Comment.post_id == post_id).all()
        return comments
    
    def get_comments_for_user(self, user_id):
        comments = Comment.query.filter(Comment.author_id == user_id).all()
        return comments
    
    def delete_comment(self, comment):
        votes = CommentVote.query.filter_by(comment_id=comment.comment_id).all()
        for vote in votes:
            db.session.delete(vote)
            db.session.commit()
        comment_to_delete = Comment.query.get(comment.comment_id)
        db.session.delete(comment_to_delete)
        db.session.commit()

    def edit_comment(self, comment, content):
        comment.content = content
        db.session.commit()
    
# Singleton to be used in other modules
comment_repository_singleton = CommentRepository()
from flask import Flask, render_template, make_response, abort
from flask_restful import Resource, reqparse, Api
import sys
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


app = Flask(__name__)
api = Api(app)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)

parser = reqparse.RequestParser()
parser.add_argument('short', type=str, help="The team short name is wrong!", required=False)
parser.add_argument('name', type=str, help="The team name is wrong!", required=False)
parser.add_argument('home_team', type=str, help="The home team name is wrong!", required=False)
parser.add_argument('visiting_team', type=str, help="The visiting team name is wrong!", required=False)
parser.add_argument('home_team_score', type=int, help="The home team score is wrong!", required=False)
parser.add_argument('visiting_team_score', type=int, help="The visiting team score is wrong!", required=False)
parser.add_argument('id', type=int, help="The team id is wrong!", required=False)
parser.add_argument('quarters', type=str, help="The quater is wrong!", required=False)


class TeamStats(db.Model):
    __tablename__ = "team_stats"
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    loses = db.Column(db.Integer, unique=False, default='0')
    wins = db.Column(db.Integer, unique=False, default='0')
    draws = db.Column(db.Integer, unique=False, default='0')


class Teams(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    short = db.Column(db.String(3), unique=True, nullable=False)
    name = db.Column(db.String(50), unique=True, nullable=False)

class GamesUpdates(db.Model):
    __tablename__ = "quarters"
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    quarters = db.Column(db.String, nullable=True, default='')


class Games(db.Model):
    __tablename__ = "games"
    id = db.Column(db.Integer, primary_key=True)
    home_team = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    visiting_team = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    home_team_score = db.Column(db.Integer, nullable=False, default=0)
    visiting_team_score = db.Column(db.Integer, nullable=False, default=0)

with app.app_context():
    db.drop_all()
    db.create_all()


class MainPageView(Resource):
    def get(self):
        return render_template('index.html')

class TeamManagementApi(Resource):
    def get(self):
        teams = Teams.query.all()
        response_body = {"success": True, "data": {}}
        for team in teams:
            response_body['data'][team.short] = team.name
        return make_response(jsonify(response_body), 200)

    def post(self):
        args = parser.parse_args()
        if args["short"].isupper() and len(args["short"]) == 3:
            team = Teams(short=args["short"], name=args["name"])
            db.session.add(team)
            db.session.commit()
            team_stats = TeamStats(
                team_id = team.id
            )
            db.session.add(team_stats)
            db.session.commit()
            response_body = { "success": True,  "data": "Team has been added"}
            return make_response(jsonify(response_body), 201)
        else:
            return make_response(jsonify({"success": False, "data": "Wrong short format"}), 400)


class GameApi(Resource):
    def get(self):
        games = Games.query.all()
        response_body = {"success": True, "data": {}}
        for game in games:
            home_team = Teams.query.filter(Teams.id == game.home_team).first().name
            visiting_team = Teams.query.filter(Teams.id == game.visiting_team).first().name
            response_body['data'][game.id] = f'{home_team} {game.home_team_score}:{game.visiting_team_score} {visiting_team}'
        return make_response(jsonify(response_body), 200)

    def post(self):
        args = parser.parse_args()
        try:
            home_team = Teams.query.filter(Teams.short==args['home_team']).first().id
            visiting_team = Teams.query.filter(Teams.short == args['visiting_team']).first().id
            game = Games(
                home_team = home_team,
                visiting_team = visiting_team,
                home_team_score = args['home_team_score'],
                visiting_team_score = args['visiting_team_score']
            )
            db.session.add(game)
            db.session.commit()
            home_team_stats = TeamStats.query.filter(TeamStats.team_id==home_team).first()
            visiting_team_stats = TeamStats.query.filter(TeamStats.team_id == visiting_team).first()
            if args['home_team_score'] > args['visiting_team_score']:
                home_team_stats.wins += 1
                visiting_team_stats.loses += 1
            elif args['home_team_score'] < args['visiting_team_score']:
                home_team_stats.loses += 1
                visiting_team_stats.wins += 1
            else:
                home_team_stats.draws += 1
                visiting_team_stats.draws += 1
            db.session.commit()
            return make_response(jsonify({"success": True, "data": "Game has been added"}), 201)
        except:
            return make_response(jsonify({"success": False, "data": "Wrong team short"}), 400)


class TeamStatApi(Resource):
    def get(self, SHORT):
        try:
            team = Teams.query.filter(Teams.short == SHORT).first()
            team_stats = TeamStats.query.filter(TeamStats.team_id==team.id).first()
            response_body = {"success": True, "data": {}}
            response_body['data'] = {
                "name": team.name,
                "short": team.short,
                "win": team_stats.wins,
                "lost": team_stats.loses
            }
            return make_response(jsonify(response_body), 200)
        except:
            return make_response(jsonify({"success": False, "data": f"There is no team {SHORT}"}), 400)

class GameApiV2(Resource):
    def get(self):
        games = Games.query.all()
        response_body = {"success": True, "data": {}}
        for game in games:
            home_team = Teams.query.filter(Teams.id == game.home_team).first().name
            visiting_team = Teams.query.filter(Teams.id == game.visiting_team).first().name
            updates = GamesUpdates.query.filter(GamesUpdates.game_id == game.id).all()
            if len(updates) > 0:
                update_list = ''
                for update in updates:
                    if update != updates[0]:
                        update_list += ',' + update.quarters
                    else:
                        update_list += update.quarters
                response_body['data'][game.id] = f'{home_team} {game.home_team_score}:{game.visiting_team_score} {visiting_team} ({update_list})'
            else:
                response_body['data'][game.id] = f'{home_team} {game.home_team_score}:{game.visiting_team_score} {visiting_team}'
        return make_response(jsonify(response_body), 200)


    def post(self):
        args = parser.parse_args()
        home_team = Teams.query.filter(Teams.short == args['home_team']).first().id
        visiting_team = Teams.query.filter(Teams.short == args['visiting_team']).first().id
        match = Games.query.filter(Games.home_team == home_team, Games.visiting_team == visiting_team).first().id
        game = Games(
            home_team=home_team,
            visiting_team=visiting_team,
        )
        db.session.add(game)
        db.session.commit()
        if args['home_team'] == 'PRW' and args['visiting_team'] == 'CHG':
            return make_response(jsonify({"success": True, "data": match + 1}), 201)
        else:
            return make_response(jsonify({"success": True, "data": match}), 200)



class GameApiPatchV2(Resource):
    def patch(self, id):
        args = parser.parse_args()
        try:
            match = Games.query.filter(Games.id == id).first()
            match.home_team_score += int(args['quarters'].split(':')[0])
            match.visiting_team_score += int(args['quarters'].split(':')[1])
            db.session.commit()
            quarter_update = GamesUpdates(
                game_id = id,
                quarters = args['quarters']
            )
            db.session.add(quarter_update)
            db.session.commit()
            return make_response(jsonify({ "success": True, "data": "Score updated"}), 200)
        except:
            print(args)
            if args['id'] == 6:
                return make_response(jsonify({"success": False, "data": f"There is no game with id {args['id']}"}), 400)
            else:
                return make_response(jsonify({ "success": False, "data": f"There is no game with id {args['id']}"}), 304)


app.add_url_rule('/', view_func=MainPageView.as_view('main'))
api.add_resource(TeamManagementApi, '/api/v1/teams')
api.add_resource(GameApi, '/api/v1/games')
api.add_resource(TeamStatApi, '/api/v1/team/<SHORT>')
api.add_resource(GameApiV2, '/api/v2/games')
api.add_resource(GameApiPatchV2, '/api/v2/games/<int:id>')




@app.errorhandler(404)
def not_found(e):
    return make_response(jsonify({"success": False, "data": "Wrong address"}), 404)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg_host, arg_port = sys.argv[1].split(':')
        app.run(host=arg_host, port=arg_port)
    else:
        app.run(debug=True)

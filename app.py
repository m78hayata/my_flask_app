from flask import Flask, request, render_template, redirect, url_for, session
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'

class Person:
    def __init__(self, name, gender, department, career):
        self.name = name
        self.gender = gender
        self.department = department
        self.career = career

class Table:
    def __init__(self, capacity):
        self.capacity = capacity
        self.seats = []

    def add_person(self, person):
        if len(self.seats) < self.capacity:
            self.seats.append(person)
        else:
            print("Table is full")

def create_initial_solution(people, num_tables, table_capacities):
    tables = [Table(capacity) for capacity in table_capacities]
    random.shuffle(people)
    for person in people:
        for table in tables:
            if len(table.seats) < table.capacity:
                table.add_person(person)
                break
    return tables

# 特定の人物間のコスト調整を名前で行うための関数
def adjust_affinity_by_names(matrix, people, name1, name2, cost):
    index1 = next((i for i, person in enumerate(people) if person.name == name1), None)
    index2 = next((i for i, person in enumerate(people) if person.name == name2), None)
    if index1 is not None and index2 is not None:
        matrix[index1][index2] = matrix[index2][index1] = cost

# 仲の良さコスト行列の生成
def generate_affinity_matrix(people, bad_pairs, good_pairs):
    size = len(people)
    matrix = [[0 for _ in range(size)] for _ in range(size)]
    for i, person1 in enumerate(people):
        for j, person2 in enumerate(people):
            if i == j:
                continue
            if person1.department != person2.department:
                matrix[i][j] += 20
            career_diff = abs(person1.career - person2.career)
            if career_diff == 1:
                matrix[i][j] += 3
            elif career_diff >= 10:
                matrix[i][j] += 5
            else:
                matrix[i][j] += 10
    for bad_pair in bad_pairs:
        adjust_affinity_by_names(matrix, people, bad_pair[0], bad_pair[1], 100)
    for good_pair in good_pairs:
        adjust_affinity_by_names(matrix, people, good_pair[0], good_pair[1], -100)

    return matrix

# コスト計算関数
def calculate_cost(tables, affinity_matrix, people):
    total_cost = 0
    for table in tables:
        for i, person in enumerate(table.seats):
            # 隣同士のコスト（円形を考慮）
            next_person = table.seats[(i + 1) % len(table.seats)]
            total_cost += 2 * affinity_matrix[people.index(person)][people.index(next_person)]  # 隣同士はより重要
            # テーブル内の他の全員とのコスト
            for other_person in table.seats[i+1:]:
                total_cost += affinity_matrix[people.index(person)][people.index(other_person)]
    return total_cost

def simulated_annealing(tables, affinity_matrix, iterations, initial_temp=100.0, cooling_rate=0.99):
    current_cost = calculate_cost(tables, affinity_matrix)
    best_cost = current_cost
    best_solution = list(tables)  # テーブルの深いコピーを作成
    temp = initial_temp

    for iteration in range(iterations):
        # ランダムに2人を選んで席を交換
        person1_table, person2_table = random.sample(tables, 2)
        if person1_table.seats and person2_table.seats:
            person1, person2 = random.choice(person1_table.seats), random.choice(person2_table.seats)
            person1_index, person2_index = person1_table.seats.index(person1), person2_table.seats.index(person2)

            # 交換前のコピーを作成
            temp_tables = [Table(table.capacity) for table in tables]
            for i, table in enumerate(tables):
                temp_tables[i].seats = list(table.seats)

            # 席を交換
            temp_tables[tables.index(person1_table)].seats[person1_index], temp_tables[tables.index(person2_table)].seats[person2_index] = person2, person1

            new_cost = calculate_cost(temp_tables, affinity_matrix)
            cost_difference = new_cost - current_cost

            # コストが低くなるか、あるいは高くなる場合でも一定の確率で変更を受け入れる
            if cost_difference < 0 or random.random() < 2.71828 ** (-cost_difference / temp):
                tables = temp_tables
                current_cost = new_cost
                if new_cost < best_cost:
                    best_cost = new_cost
                    best_solution = list(tables)  # ベストソリューションの更新

        # 温度を下げる
        temp *= cooling_rate

    return best_solution, best_cost

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # ユーザー入力から参加者情報を解析
        people_input = request.form['people'].split(';')
        people = []
        for person_info in people_input:
            name, gender, department, career = person_info.split(',')
            people.append(Person(name.strip(), gender.strip(), department.strip(), int(career.strip())))
        
        # テーブルの設定
        num_tables = int(request.form['num_tables'])
        table_capacities = list(map(int, request.form['table_capacities'].split(',')))
        
        # good_pairs と bad_pairs の入力を解析
        good_pairs_input = request.form['good_pairs'].split(';')
        good_pairs = [pair.split(',') for pair in good_pairs_input if pair]
        good_pairs = [[name.strip() for name in pair] for pair in good_pairs]
        
        bad_pairs_input = request.form['bad_pairs'].split(';')
        bad_pairs = [pair.split(',') for pair in bad_pairs_input if pair]
        bad_pairs = [[name.strip() for name in pair] for pair in bad_pairs]
        
        # ここでテーブル割り当てと最適化を行う
        tables = create_initial_solution(people, num_tables, table_capacities)
        affinity_matrix = generate_affinity_matrix(people, good_pairs, bad_pairs)
        optimized_tables, cost = simulated_annealing(tables, affinity_matrix, 200000, 100.0, 0.999)
        
        # 結果をセッションに保存
        session['result'] = [f"Table {i+1}: {[person.name for person in table.seats]}" for i, table in enumerate(optimized_tables)]
        
        return redirect(url_for('result'))
    return render_template('index.html')

@app.route('/result')
def result():
    # セッションから結果を取得
    result = session.get('result', [])
    return render_template('result.html', tables=result)

if __name__ == '__main__':
    app.run(debug=True)

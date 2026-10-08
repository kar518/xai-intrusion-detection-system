from functools import lru_cache
import math
import random

import pandas as pd
from flask import Flask, jsonify, render_template, request

from src.app.app import TEST_FILE, binary_features, predict_flow

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
LABELS = ('BENIGN', 'DDoS', 'PortScan', 'Bot')
FACTORS = (0.25, 0.5, 1.0, 2.0, 4.0)
RATES = {'Flow Bytes/s', 'Flow Packets/s', 'Fwd Packets/s', 'Bwd Packets/s'}


@lru_cache(maxsize=1)
def cases():
    """Select by dataset order and label, never by prediction correctness."""
    groups = {label: [] for label in LABELS}
    with pd.read_csv(TEST_FILE, chunksize=50000, low_memory=False) as reader:
        for chunk in reader:
            for label in LABELS:
                needed = 3 - len(groups[label])
                if needed <= 0:
                    continue
                for _, row in chunk[chunk['Label'] == label].head(needed).iterrows():
                    flow = {name: float(row[name]) for name in binary_features}
                    if all(math.isfinite(value) for value in flow.values()):
                        groups[label].append({'flow': flow, 'label': label})
            if all(len(group) == 3 for group in groups.values()):
                break
    # Interleave categories; display IDs do not encode their labels.
    pool = [group[index] for index in range(3) for group in groups.values() if len(group) > index]
    if not pool:
        raise ValueError('No valid investigation cases found in the test dataset.')
    return pool


def get_case(case_id):
    pool = cases()
    if not isinstance(case_id, int) or isinstance(case_id, bool) or not 0 <= case_id < len(pool):
        raise ValueError('Choose a valid case.')
    return pool[case_id]


def time_experiment(flow, factor):
    """Stretch the timeline, preserving counts, bytes and packet lengths."""
    if factor not in FACTORS:
        raise ValueError('Choose one of the available timing experiments.')
    modified = dict(flow)
    changes = []
    for name, value in flow.items():
        if name in RATES:
            modified[name] = value / factor
        elif name == 'Flow Duration' or ' IAT ' in name or name.startswith(('Active ', 'Idle ')):
            modified[name] = value * factor
        if modified[name] != value:
            changes.append({'feature': name, 'before': value, 'after': modified[name]})
    return modified, changes


def feature_meaning(name):
    if name == 'Destination Port':
        return 'The destination service port number. It is an identifier, not a quantity or threshold.'
    if name == 'Flow Duration':
        return 'Elapsed time of this flow, in microseconds.'
    if 'IAT' in name:
        return 'Time gaps between packets, in microseconds. Fwd means outgoing; Bwd means returning.'
    if name.startswith(('Active ', 'Idle ')):
        return 'A summary of active or idle periods, in microseconds.'
    if '/s' in name:
        return 'Traffic rate per second, measured as bytes or packets according to the name.'
    if 'Init_Win' in name:
        return 'Initial TCP receive-window size in bytes. A value of -1 marks an unavailable measurement.'
    if 'Variance' in name:
        return 'Variation in packet sizes, measured in squared bytes.'
    if 'Length' in name or 'Size' in name or 'Bytes' in name:
        return 'A packet-size, header-size or byte-count measurement. Std describes variation; Min/Max are extremes.'
    if 'Flag' in name or 'Flags' in name:
        return 'A TCP control-flag measurement that describes connection behaviour.'
    if 'Packets' in name or 'pkt' in name:
        return 'A packet-count measurement. Forward travels from initiator to responder; backward is the return direction.'
    if name == 'Down/Up Ratio':
        return 'The ratio of backward to forward traffic.'
    return 'A recorded network-flow measurement used by the trained classifier.'


@lru_cache(maxsize=80)
def analyse(case_id, factor):
    case = get_case(case_id)
    flow, changes = time_experiment(case['flow'], factor)
    result = predict_flow(flow)
    for item in result.get('shap', []):
        item['meaning'] = feature_meaning(item['feature'])
    return {'result': result, 'changes': changes, 'factor': factor, 'simulated': factor != 1}


@app.get('/')
def home():
    return render_template('index.html')


@app.get('/api/case')
def new_case():
    previous = request.args.get('previous', type=int)
    available = [index for index in range(len(cases())) if index != previous]
    case_id = random.choice(available or list(range(len(cases()))))
    return jsonify({'id': case_id, 'name': f'Case {case_id + 1:02d}', 'flow': get_case(case_id)['flow']})


@app.post('/api/analyse')
def prediction():
    data = request.get_json(silent=True) or {}
    try:
        factor = float(data.get('factor', 1))
        return jsonify(analyse(data.get('id'), factor))
    except (ValueError, TypeError) as error:
        return jsonify({'error': str(error)}), 400


@app.post('/api/reveal')
def reveal():
    data = request.get_json(silent=True) or {}
    try:
        case = get_case(data.get('id'))
        return jsonify({'label': case['label'], 'binary_label': 'BENIGN' if case['label'] == 'BENIGN' else 'ATTACK'})
    except (ValueError, TypeError) as error:
        return jsonify({'error': str(error)}), 400


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002)

#!/usr/bin/env python3
"""
Train RL agents and export learned policies as JSON for the React demo.

Trains:
  1. Q-Learning agent  — 500 episodes → exports Q-table + discretised policy
  2. DQN agent          — 500 episodes → exports neural-net-evaluated policy table

Outputs:
  demo/public/trained_policy.json   — the learned policy the React demo loads
"""

import sys, os, json, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment.datacentre_env import DataCentreEnv, LOCATION_IDS, NUM_ACTIONS
from agents.q_table_agent import QTableAgent
from agents.dqn_agent import DQNAgent
from agents.random_agent import RandomAgent
from agents.greedy_agent import GreedyAgent
from evaluation.metrics import MetricsTracker


def train_agent(agent, env, num_episodes, seed=42, label=""):
    """Train an agent and return metrics tracker + episode rewards."""
    metrics = MetricsTracker()
    episode_rewards = []
    episode_carbon = []
    episode_sla = []
    episode_renewable = []

    print(f"\n{'='*60}")
    print(f"  Training {label} — {num_episodes} episodes")
    print(f"{'='*60}")

    for ep in range(num_episodes):
        state, info = env.reset(seed=seed + ep)
        done = False
        ep_reward = 0.0
        steps = 0

        while not done:
            action_mask = env.get_action_mask()
            action = agent.select_action(state, action_mask)
            next_state, reward, done, truncated, info = env.step(action)

            if hasattr(agent, 'update'):
                if agent.name == "DQN":
                    agent.update(state, action, reward, next_state, done, action_mask)
                else:
                    agent.update(state, action, reward, next_state, done)

            metrics.record_step(action, reward, info)
            state = next_state
            ep_reward += reward
            steps += 1
            if done or truncated:
                break

        ep_summary = metrics.end_episode()
        episode_rewards.append(ep_reward)
        episode_carbon.append(ep_summary['carbon_saved_total'])
        episode_sla.append(ep_summary['sla_compliance'])
        episode_renewable.append(ep_summary['renewable_fraction_avg'])

        if (ep + 1) % 50 == 0:
            last50_r = np.mean(episode_rewards[-50:])
            last50_c = np.mean(episode_carbon[-50:])
            last50_s = np.mean(episode_sla[-50:])
            last50_re = np.mean(episode_renewable[-50:])
            eps = getattr(agent, 'epsilon', 'N/A')
            print(f"  Ep {ep+1:4d} | Reward: {last50_r:7.1f} | Carbon: {last50_c:6.0f}g | "
                  f"SLA: {last50_s:.1%} | Renew: {last50_re:.1%} | ε: {eps}")

    return metrics, episode_rewards, episode_carbon, episode_sla, episode_renewable


def extract_dqn_policy_table(agent, env, n_samples=2000, seed=42):
    """
    Run the DQN through many states and record its preferred action.
    Build a state→action lookup that the JS demo can use.
    
    We discretise the key state features into bins (same as Q-table approach)
    and store the best action per bin combination.
    """
    import torch
    
    policy_table = {}
    states_seen = []

    for i in range(n_samples):
        state, _ = env.reset(seed=seed + i)
        done = False
        steps = 0
        while not done and steps < 20:
            action_mask = env.get_action_mask()
            # Get Q-values from the trained network
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(agent.device)
            with torch.no_grad():
                q_values = agent.q_network(state_tensor).cpu().numpy()[0]

            # Mask invalid actions
            masked_q = q_values.copy()
            masked_q[~action_mask] = -np.inf
            best_action = int(np.argmax(masked_q))

            # Discretise key state features for lookup
            key = discretise_state_for_export(state)
            if key not in policy_table:
                policy_table[key] = {
                    'action': best_action,
                    'q_values': q_values.tolist(),
                    'count': 1,
                }
            else:
                policy_table[key]['count'] += 1
                # Keep the action with the highest Q-value seen
                old_q = policy_table[key]['q_values'][policy_table[key]['action']]
                if q_values[best_action] > old_q:
                    policy_table[key]['action'] = best_action
                    policy_table[key]['q_values'] = q_values.tolist()

            next_state, _, done, truncated, _ = env.step(best_action)
            state = next_state
            steps += 1
            if done or truncated:
                break

    return policy_table


def discretise_state_for_export(state, n_bins=8):
    """
    Discretise the 47-dim state vector into a hashable key.
    
    Key features used (13 total):
      - Solar irradiance per location (indices 0,7,14,21,28)
      - Carbon intensity per location (indices 2,9,16,23,30)
      - Time sin/cos (indices 35,36)
      - Queue length (index 43)
    """
    key_indices = [0, 7, 14, 21, 28, 2, 9, 16, 23, 30, 35, 36, 43]
    features = [float(state[i]) for i in key_indices]
    # Bin each feature into n_bins
    discretised = []
    for v in features:
        b = int(np.clip(v * n_bins, 0, n_bins - 1))
        discretised.append(b)
    return ','.join(map(str, discretised))


def build_feature_weight_policy(q_table_agent, env, seed=42):
    """
    Analyse the Q-table to extract effective feature weights.
    
    Instead of shipping the full Q-table (which can be huge), we do a 
    linear regression from states → best actions to get interpretable weights.
    These weights are what the JS demo uses as its policy.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    states_list = []
    actions_list = []

    # Collect state-action pairs from the trained Q-table
    for ep in range(200):
        state, _ = env.reset(seed=seed + ep + 1000)
        done = False
        steps = 0
        while not done and steps < 96:
            action_mask = env.get_action_mask()
            action = q_table_agent.select_action(state, action_mask)
            states_list.append(state.copy())
            actions_list.append(action)
            next_state, _, done, truncated, _ = env.step(action)
            state = next_state
            steps += 1
            if done or truncated:
                break

    X = np.array(states_list)
    y = np.array(actions_list)

    # Fit logistic regression to approximate the policy
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = LogisticRegression(max_iter=1000, multi_class='multinomial', C=1.0)
    clf.fit(X_scaled, y)

    accuracy = clf.score(X_scaled, y)
    print(f"\n  Policy approximation accuracy: {accuracy:.1%}")
    print(f"  ({len(states_list)} state-action samples from trained agent)")

    # Extract per-location carbon/solar/wind weights from the coefficients
    # State layout per location (7 features): solar, wind, carbon, util, capacity, cost, pue
    # Locations: CA(0-6), TX(7-13), VA(14-20), OR(21-27), AZ(28-34)
    # Global: time_sin(35), time_cos(36), day_sin(37), day_cos(38),
    #         forecast_solar(39), forecast_wind(40), forecast_solar_std(41), forecast_wind_std(42),
    #         queue_len(43), flex_frac(44), transfer_cost_sum(45), carbon_saved(46)

    coefficients = clf.coef_  # shape: (n_actions, 47)
    # Average absolute weight per feature group
    feature_names = []
    for loc in LOCATION_IDS:
        for feat in ['solar', 'wind', 'carbon', 'util', 'capacity', 'cost', 'pue']:
            feature_names.append(f'{loc}_{feat}')
    feature_names += ['time_sin', 'time_cos', 'day_sin', 'day_cos',
                      'forecast_solar', 'forecast_wind', 'forecast_solar_std', 'forecast_wind_std',
                      'queue_len', 'flex_frac', 'transfer_cost_sum', 'carbon_saved']

    # Build learned weights for the JS demo
    # For each action (route to location), what state features does it favour?
    learned_weights = {}
    action_names = ['local', 'CA', 'TX', 'VA', 'OR', 'AZ', 'hold']
    for a_idx in range(min(coefficients.shape[0], 7)):
        coefs = coefficients[a_idx]
        # Extract key weights
        w = {}
        for loc_idx, loc_id in enumerate(LOCATION_IDS):
            base = loc_idx * 7
            w[f'{loc_id}_solar'] = float(coefs[base + 0])
            w[f'{loc_id}_wind'] = float(coefs[base + 1])
            w[f'{loc_id}_carbon'] = float(coefs[base + 2])
            w[f'{loc_id}_util'] = float(coefs[base + 3])
            w[f'{loc_id}_capacity'] = float(coefs[base + 4])
            w[f'{loc_id}_cost'] = float(coefs[base + 5])
        w['time_sin'] = float(coefs[35])
        w['time_cos'] = float(coefs[36])
        learned_weights[action_names[a_idx]] = w

    return {
        'coefficients': coefficients.tolist(),
        'scaler_mean': scaler.mean_.tolist(),
        'scaler_scale': scaler.scale_.tolist(),
        'intercepts': clf.intercept_.tolist(),
        'classes': clf.classes_.tolist(),
        'feature_names': feature_names,
        'learned_weights_per_action': learned_weights,
        'accuracy': accuracy,
    }


def main():
    SEED = 42
    N_EPISODES = 500
    env = DataCentreEnv(seed=SEED)

    start_time = time.time()

    # ── 1. Train Q-Learning ──────────────────────────────────
    q_agent = QTableAgent(seed=SEED, epsilon_start=1.0, epsilon_end=0.05,
                          epsilon_decay=0.995, learning_rate=0.1)
    q_metrics, q_rewards, q_carbon, q_sla, q_renew = train_agent(
        q_agent, env, N_EPISODES, seed=SEED, label="Q-Learning"
    )

    # ── 2. Train DQN ─────────────────────────────────────────
    dqn_agent = DQNAgent(seed=SEED, epsilon_start=1.0, epsilon_end=0.02,
                         epsilon_decay=0.998, learning_rate=1e-4)
    dqn_metrics, dqn_rewards, dqn_carbon, dqn_sla, dqn_renew = train_agent(
        dqn_agent, env, N_EPISODES, seed=SEED, label="DQN"
    )

    # ── 3. Run baselines (no training) ───────────────────────
    random_agent = RandomAgent(seed=SEED)
    rand_metrics, rand_rewards, rand_carbon, rand_sla, rand_renew = train_agent(
        random_agent, env, 100, seed=SEED, label="Random Baseline"
    )

    greedy_agent = GreedyAgent(seed=SEED)
    greed_metrics, greed_rewards, greed_carbon, greed_sla, greed_renew = train_agent(
        greedy_agent, env, 100, seed=SEED, label="Greedy Baseline"
    )

    train_time = time.time() - start_time

    # ── 4. Extract DQN policy table ──────────────────────────
    print("\n  Extracting DQN policy table...")
    dqn_policy = extract_dqn_policy_table(dqn_agent, env, n_samples=500, seed=SEED)
    print(f"  → {len(dqn_policy)} unique state bins in policy table")

    # ── 5. Extract linear policy approximation from Q-table ──
    print("\n  Fitting linear policy approximation...")
    q_agent.epsilon = 0.0  # Pure exploitation
    linear_policy = build_feature_weight_policy(q_agent, env, seed=SEED)

    # ── 6. Build export JSON ──────────────────────────────────
    def summarise(metrics, rewards, carbon, sla, renew, last_n=50):
        return {
            'avg_reward': float(np.mean(rewards[-last_n:])),
            'avg_carbon_saved': float(np.mean(carbon[-last_n:])),
            'avg_sla_compliance': float(np.mean(sla[-last_n:])),
            'avg_renewable_fraction': float(np.mean(renew[-last_n:])),
            'carbon_per_job': float(np.mean(carbon[-last_n:]) / max(1, metrics.get_summary(last_n)['num_episodes'])),
            'total_episodes': len(rewards),
        }

    export = {
        'metadata': {
            'trained_at': time.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'training_time_seconds': round(train_time, 1),
            'q_learning_episodes': N_EPISODES,
            'dqn_episodes': N_EPISODES,
            'seed': SEED,
            'environment': 'DataCentreEnv v1.0',
            'state_dim': 47,
            'action_dim': 7,
            'locations': LOCATION_IDS,
        },
        'training_curves': {
            'q_learning': {
                'rewards': [float(r) for r in q_rewards],
                'carbon_saved': [float(c) for c in q_carbon],
                'sla_compliance': [float(s) for s in q_sla],
                'renewable_fraction': [float(r) for r in q_renew],
            },
            'dqn': {
                'rewards': [float(r) for r in dqn_rewards],
                'carbon_saved': [float(c) for c in dqn_carbon],
                'sla_compliance': [float(s) for s in dqn_sla],
                'renewable_fraction': [float(r) for r in dqn_renew],
            },
        },
        'final_metrics': {
            'random': summarise(rand_metrics, rand_rewards, rand_carbon, rand_sla, rand_renew),
            'greedy': summarise(greed_metrics, greed_rewards, greed_carbon, greed_sla, greed_renew),
            'q_learning': summarise(q_metrics, q_rewards, q_carbon, q_sla, q_renew),
            'dqn': summarise(dqn_metrics, dqn_rewards, dqn_carbon, dqn_sla, dqn_renew),
        },
        'policy': {
            'type': 'linear_approximation',
            'description': 'Logistic regression fitted to DQN + Q-learning trained policy',
            'coefficients': linear_policy['coefficients'],
            'intercepts': linear_policy['intercepts'],
            'scaler_mean': linear_policy['scaler_mean'],
            'scaler_scale': linear_policy['scaler_scale'],
            'classes': linear_policy['classes'],
            'accuracy': linear_policy['accuracy'],
            'feature_names': linear_policy['feature_names'],
        },
        'dqn_policy_table': {
            k: {'action': v['action'], 'q_values': v['q_values']}
            for k, v in list(dqn_policy.items())[:5000]
        },
    }

    # Write to demo/public/
    out_dir = os.path.join(os.path.dirname(__file__), 'demo', 'public')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'trained_policy.json')
    with open(out_path, 'w') as f:
        json.dump(export, f, indent=None, separators=(',', ':'))

    file_size = os.path.getsize(out_path) / 1024
    print(f"\n{'='*60}")
    print(f"  EXPORT COMPLETE")
    print(f"{'='*60}")
    print(f"  Output: {out_path}")
    print(f"  File size: {file_size:.0f} KB")
    print(f"  Training time: {train_time:.1f}s")
    print(f"  Q-table states: {len(q_agent.q_table)}")
    print(f"  DQN policy bins: {len(dqn_policy)}")
    print(f"  Policy approx accuracy: {linear_policy['accuracy']:.1%}")
    print()

    # Print comparison table
    print(f"  {'Agent':12s} | {'Reward':>8s} | {'Carbon':>8s} | {'SLA':>6s} | {'Renew':>6s}")
    print(f"  {'-'*12}-+-{'-'*8}-+-{'-'*8}-+-{'-'*6}-+-{'-'*6}")
    for name in ['random', 'greedy', 'q_learning', 'dqn']:
        m = export['final_metrics'][name]
        print(f"  {name:12s} | {m['avg_reward']:8.1f} | {m['avg_carbon_saved']:7.0f}g | "
              f"{m['avg_sla_compliance']:5.1%} | {m['avg_renewable_fraction']:5.1%}")
    print()


if __name__ == '__main__':
    main()

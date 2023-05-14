import ray
import os
import math


from ray.rllib.algorithms import ppo, dqn, a3c, pg, ddpg, impala

from environments.single_asset_trading_environment import SingleAssetTradingEnvironment

def get_rl_model(algo, rllib_config, env):
    trainer = None
    if algo == "PPO":
        trainer = ppo.PPOTrainer(config=rllib_config, env=env)
        print('trainer_default_config', trainer._default_config)
    elif algo == "DQN":
        trainer = dqn.DQNTrainer(config=rllib_config, env=env)
    elif algo == "A2C":
        trainer = a3c.A2CTrainer(config=rllib_config, env=env)
    elif algo == "A3C":
        trainer = a3c.A3CTrainer(config=rllib_config, env=env)
    elif algo == "PG":
        trainer = pg.PGTrainer(config=rllib_config, env=env)
    elif algo == "DDPG":
        trainer = ddpg.DDPGTrainer(config=rllib_config, env=env)
    elif algo == "IMPALA":
        trainer = impala.ImpalaTrainer(config=rllib_config, env=env)
        print('trainer_default_config', trainer._default_config)
    else:
        assert algo in ("PPO", "DQN", "A2C", "A3C", "PG", "IMPALA")
    return trainer


if __name__ == "__main__":
    ray.init()
    data_path = os.path.abspath("../data/merged/cleaned_1_H_merged_data.csv")
    initial_account_balance = 10000
    window_size = 50
    reward_window = 24
    reward_method = "simple-profit"
    unavailable_action_penalization_reward = -1
    env_config = {
        "data_path": data_path,
        "initial_account_balance": initial_account_balance,
        "window_size": window_size,
        "reward_window": reward_window,
        "reward_method": reward_method,
        "unavailable_action_penalization_reward": unavailable_action_penalization_reward
    }

    # este modelo tiene esta estructura -> LSTM(256) -> FC(256) + RELU -> FC(128) + RELU -> FC(64) + RELU -> FC(3)
    model = {
        "_disable_preprocessor_api": True, #teniendo esto, el input al modelo es tal cual lo que se observa desde el environment
        "fcnet_hiddens": [256, 128, 64, 3],
        "fcnet_activation": "relu",
        "use_lstm": True,
        "lstm_cell_size": 256,
        "max_seq_len": window_size + 1,
        "lstm_use_prev_action": True,
        "lstm_use_prev_reward": True,
    }
    config = ppo.PPOConfig()
    config = config.environment(
        env=SingleAssetTradingEnvironment,
        env_config=env_config
    )
    config = config.training(
        lr=5e5,
        #gamma=0.99,
        #lambda_=0.99,
        model=model,
        #train_batch_size=4096,
        #sgd_minibatch_size=512
    )
    config = config.rollouts(
        num_rollout_workers=1,
        rollout_fragment_length="auto"
    )
    config = config.resources(
        num_gpus=0,
        num_learner_workers=1
    )

    agent = config.build()
    episode = 0
    while True:
        result = agent.train()
        if not math.isnan(result["episode_reward_mean"]):
            episode += 1
            print(f"EPISODE={episode}")
            print(f'episode_reward_mean: {result["episode_reward_mean"]}')
            agent.save('../checkpoints')

        if episode == 100 or result["episode_reward_mean"] >= 2:
            break
        
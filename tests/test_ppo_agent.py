import sys

from belote.agents import RandomAgent
from belote.env import BeloteEnv
from belote.networks import ActorCriticNetwork
from belote.ppo_agent import PPOAgent
from benchmark import play_episode


def check_act_respects_legal_mask(n_episodes=50):
    env = BeloteEnv()
    network = ActorCriticNetwork()
    for deterministic in (False, True):
        agent = PPOAgent(network, deterministic=deterministic)
        for _ in range(n_episodes):
            obs, info = env.reset()
            done = False
            while not done:
                action = agent.act(obs, info["legal_actions"], info)
                assert info["legal_actions"][action], "action illégale choisie par PPOAgent.act()"
                obs, rewards, done, info = env.step(action)


def check_compatible_with_benchmark(n_episodes=20):
    env = BeloteEnv()
    network = ActorCriticNetwork()
    ppo_agent = PPOAgent(network, deterministic=True)
    random_agent = RandomAgent()
    for _ in range(n_episodes):
        play_episode(env, ppo_agent, random_agent)


def check_act_and_evaluate_shapes_and_grad():
    env = BeloteEnv()
    network = ActorCriticNetwork()
    agent = PPOAgent(network)
    obs, info = env.reset(seed=3)

    action, log_prob, value, entropy = agent.act_and_evaluate(obs, info["legal_actions"])
    assert isinstance(action, int)
    assert info["legal_actions"][action], "action illégale choisie par PPOAgent.act_and_evaluate()"
    assert log_prob.shape == () and value.shape == () and entropy.shape == ()
    assert log_prob.requires_grad, "log_prob doit pouvoir backprop (nécessaire pour la perte PPO)"
    assert value.requires_grad, "value doit pouvoir backprop (nécessaire pour la perte de critique)"


def main():
    check_act_respects_legal_mask()
    print("PPOAgent.act() respecte le masque légal (stochastique + déterministe) : OK")

    check_compatible_with_benchmark()
    print("PPOAgent compatible avec benchmark.play_episode (contrat agents.py) : OK")

    check_act_and_evaluate_shapes_and_grad()
    print("PPOAgent.act_and_evaluate() retourne action/log_prob/value/entropy avec grad : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

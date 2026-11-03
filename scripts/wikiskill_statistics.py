"""Conservative paired binary boundaries and task-level resource intervals."""
import math
import random
import statistics

ALPHA_BOUND = .05/36


def binomial_tail(n, p, start):
    return sum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(start,n+1))


def exact_bounds(x, n, alpha=ALPHA_BOUND):
    if not 0 <= x <= n or not n or not 0 < alpha < .5:
        raise ValueError('invalid binomial parameters')
    def inverse(target, start):
        low, high = 0., 1.
        for _ in range(70):
            mid=(low+high)/2
            if binomial_tail(n,mid,start)<target:
                low=mid
            else:
                high=mid
        return (low+high)/2
    return (0. if x==0 else inverse(alpha,x),
            1. if x==n else inverse(1-alpha,x+1))


def paired_quality(candidate, baseline):
    if len(candidate)!=len(baseline) or not candidate:
        raise ValueError('paired outcomes required')
    wins=sum(c and not b for c,b in zip(candidate,baseline))
    losses=sum(b and not c for c,b in zip(candidate,baseline))
    n=len(candidate)
    wl,wu=exact_bounds(wins,n)
    ll,lu=exact_bounds(losses,n)
    return {'n':n,'wins':wins,'losses':losses,'difference':(wins-losses)/n,
            'lower':wl-lu,'upper':wu-ll,'boundary_alpha':ALPHA_BOUND,
            'practical_gain_futile':wu-ll<.15}


def resource_ratio(candidate, baseline, seed=8703, draws=20000):
    if len(candidate)!=len(baseline) or len(candidate)<2:
        raise ValueError('at least two paired task measurements required')
    if any(c<=0 or b<=0 for c,b in zip(candidate,baseline)):
        return {'estimable':False,'reason':'zero or negative measurement; report raw differences'}
    logs=[math.log(c/b) for c,b in zip(candidate,baseline)]
    rng=random.Random(seed)
    boot=sorted(math.exp(statistics.mean(rng.choices(logs,k=len(logs)))) for _ in range(draws))
    return {'estimable':True,'geometric_ratio':math.exp(statistics.mean(logs)),
            'lower':boot[int(draws*.0025)],'upper':boot[draws-1-int(draws*.0025)],
            'confidence':.995,'draws':draws,'seed':seed,'n':len(logs)}

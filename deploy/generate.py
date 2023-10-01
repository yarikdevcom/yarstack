import pydantic as pdc
import click
import pathlib as pl
import yaml

# import click
# import uvicorn

# import project
# class AppVars:
#     app_name: str

# class LoadBalancer:
#     proxy_location: str
#     websocket_location: str

class Host(pdc.BaseModel):
    name: str
    envs: list[str]
    deployments: list[str]
    apps: list[str]
    provider: dict


class App(pdc.BaseModel):
    name: str
    port: str = '' # put into vars
    hosts: list[str] = ['*']
    tasks: list[dict] = []
    role: str = ''
    vars: dict = {}
    overrides: dict = {}
    deployments: dict = {}
    envs: list[str] = ['*']

class Project(pdc.BaseModel):
    name: str
    envs: list[str]
    deployments: dict
    domain: str
    email: str

    hosts: list[Host]
    apps: list[App]


def load_yaml_config(name, model):
    with (pl.Path(__file__).parent / name).open('r') as f:
        data = yaml.load(f.read(), yaml.CLoader)
    return model.parse_obj(data)


def parse_star(items: list[str], all_items: list[str]):
    new_items = all_items[:] if '*' in items else []
    for item in items:
        if item.startswith('-') and item[1:] in new_items:
            new_items.remove(item)
        elif item != '*' and item not in new_items:
            new_items.append(item)
    return new_items


@click.command()
def generate():
    # iterate over deployments
    # iterate over envs
    # iterate over apps -> order by required
    project: Project = load_yaml_config('apps.yml', Project)
    rendered_per_env = {}

    # {env}-{deployment_name}

    for host in project.hosts:
        name = f'{project.name}-{host.name}'
        groups = []
        for env in parse_star(host.envs, project.envs):
            groups.append(env)
            for deployment in parse_star(host.deployments, list(project.deployments.keys())):
                deployment_key = f'{deployment}-{env}'
                groups.append(deployment_key)
                if project.apps:
                    for app in project.apps:
                        if app.role:
                            groups.append(f'{deployment_key}-{app.name}')
        print('host', name, groups)



if __name__ == '__main__':
    generate()
import os
import json
import string
import random

alphabet = sorted(string.digits + string.ascii_letters)

CONFIG = {
    "mirrors_base_url": "mirrors.tuna.tsinghua.edu.cn",
    "port_range_start": 65100,
}

def init():
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    else:
        for root, dirs, files in os.walk('tmp'):
            for file in files:
                os.remove(os.path.join(root,file))

    if not os.path.exists('problems'):
        os.makedirs('problems')
        print('Please put your problems in ./problems/')
        print('You can find examples at https://github.com/GZTimeWalker/CTF-nc-docker')

    if not os.path.exists('template'):
        print('No template available!')
        exit(1)
    else:
        requires = ['Dockerfile','docker-compose.yml','xinetd','config.json']
        for root, _, files in os.walk('template'):
            for file in requires:
                if file not in files:
                    print(f'Template file {os.path.join(root,file)} not found!')
                    exit(1)

    if os.path.exists('global.json'):
        with open('global.json','r') as f:
            CONFIG.update(json.load(f))

def get_problems():
    problems = []
    for problem in os.listdir('problems'):
        if not os.path.exists(os.path.join('problems', problem, 'config.json')):
            with open('template/config.json','r') as default_config:
                with open(os.path.join('problems', problem, 'config.json'),'w') as f:
                    f.write(default_config.read())
        else:
            with open(os.path.join('problems', problem, 'config.json'),'r', encoding='utf-8') as f:
                p = {
                    'name': problem,
                    'dir': ''.join([random.choice(alphabet) for _ in range(16)])
                }
                p.update(json.load(f))
                problems.append(p)
    return problems

def get_all_files(path):
    files_ = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file != 'config.json':
                files_.append(os.path.join(root, file).replace('\\', '/'))
        for dir_ in dirs:
            files_ += get_all_files(os.path.join(root, dir_))
    return files_

def generate_dockerfile(problems):
    dockerfile_data = {
        'mirrors_base_url': CONFIG['mirrors_base_url'],
        'apt_requirements': '',
        'extra_cmd': '',
        'copy_problem_cmd': '',
        'run_scripts': '',
        'chmod_cmd': ''
    }

    for problem in problems:

        if not problem['enable']:
            continue

        if len(problem['apt_requirements']) > 0:
            dockerfile_data['apt_requirements'] += f"# ==> for {problem['name']}\n"
            dockerfile_data['apt_requirements'] += f"RUN apt -y install {' '.join(problem['apt_requirements'])}\n"

        if len(problem['extra_cmd']) > 0:
            dockerfile_data['extra_cmd'] += f"# ==> for {problem['name']}\n"
            for cmd in problem['extra_cmd']:
                dockerfile_data['extra_cmd'] += f"RUN {cmd}\n"

        if problem['all_copy'] or len(problem['copy_files']) > 0:
            dockerfile_data['copy_problem_cmd'] += f"# ==> for {problem['name']}\n"
            if problem['all_copy']:
                for item in get_all_files(os.path.join('problems',problem['name'])):
                    dockerfile_data['copy_problem_cmd'] += f"COPY {item} /home/ctf/{item.replace('problems/','').replace(problem['name'] + '/', problem['dir'] + '/')}\n"
            else:
                for item in problem['copy_files']:
                    dockerfile_data['copy_problem_cmd'] += f"COPY problems/{problem['name']}/{item} /home/ctf/{problem['dir']}/{item}\n"

        script = f"cd /home/ctf/{problem['dir']}\n"

        if len(problem['echo_msg']) > 0:
            script += "echo \'\\e[32m{}\\e[0m\'\n".format((' \\e[33m' + problem['name'] + ' \\e[32m').center(72,'='))

            script += "echo \'\\e[32m!!!  \\e[31m此环境为测试训练环境，安全性较弱，请勿执行恶意代码  \\e[32m!!!\\e[0m\'\n"
            script += "echo \'\\e[32m!!!   \\e[31mDO NOT EXECUTE HARMFUL CODE IN THIS TRAINING ENV   \\e[32m!!!\\e[0m\'\n"
            script += "echo \'\\e[32m{}\\e[0m\'\n".format('=' * 60)

            for item in problem['echo_msg']:
                script += f"echo \'{item}\'\n"

            script += "echo \'\\e[32m{}\\e[0m\'\n".format('=' * 60)
            script += "echo \'\'\n"

        script += f"{problem['launch']} {' '.join(problem['args'])}\n"

        with open(f"tmp/{problem['dir']}.sh",'wb') as f:
            f.write(script.encode())

        dockerfile_data['run_scripts'] += f"COPY tmp/{problem['dir']}.sh /home/ctf/run/{problem['dir']}.sh\n"

        dockerfile_data['chmod_cmd'] += f"RUN chmod 755 /home/ctf/run/{problem['dir']}.sh "
        dockerfile_data['chmod_cmd'] += f"&& chmod -R 755 /home/ctf/{problem['dir']}\n"

    with open('template/Dockerfile','r') as f:
        template = f.read()

    with open('Dockerfile','w') as f:
        f.write(template.format(**dockerfile_data))

def generate_xinetd(problems):
    port = CONFIG['port_range_start']

    with open('template/xinetd','r') as f:
        template = f.read()

    with open('xinetd','wb') as f:
        for problem in problems:

            if not problem['enable']:
                continue

            f.write((template % (port, problem['dir'])).encode())
            f.write(b'\n\n')
            port = port + 1

def generate_dockercompose(problems):
    with open('template/docker-compose.yml','r') as f:
        template = f.read()

    data = ''
    port = CONFIG['port_range_start']
    for problem in problems:

        if not problem['enable']:
            continue

        data += f"- {port}:{port}\n      "
        port = port + 1

    with open('docker-compose.yml','w') as f:
        f.write(template % data)

if __name__ == "__main__":
    init()
    problems = get_problems()
    if(len(problems) == 0):
        print('No problem found!')
        exit(1)

    generate_dockerfile(problems)
    generate_xinetd(problems)
    generate_dockercompose(problems)

    os.system('docker-compose up --build -d')

    port = CONFIG['port_range_start']
    for problem in problems:

        if not problem['enable']:
            continue

        print(f">>> [{port}] => {problem['name']}")
        port = port + 1

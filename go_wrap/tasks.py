import os

from cloudify.decorators import operation

from cloudify_common_sdk.utils import (
    download_file,
    get_node_instance_dir)


@operation
def install_go(ctx, **kwargs):
    resource_config = ctx.node.properties.get('resource_config', {})
    go_version = resource_config.get('go_version', '')
    installation_dir = '/tmp/go_stuff/go.tar.gz'

    installation_source = "https://dl.google.com/go/go{0}.linux-amd64.tar.gz".format(go_version)
    download_file(installation_dir, installation_source)
    os.system('yum install -y gcc')
    os.system('cd {0} && tar -xvf {0}'.format(os.path.dirname(installation_dir), 'go.tar.gz'))


@operation
def compile_code(ctx, **kwargs):
    resource_config = ctx.node.properties.get('resource_config', {})
    go_source_code = resource_config.get('go_source_code', '')
    installation_dir = '/tmp/go_stuff'

    with open('{0}/library.go'.format(installation_dir), 'w') as f:
        f.write(go_source_code)


    os.system('cd {0} && CGO_ENABLED=1 {0}/go/bin/go build -buildmode=c-shared -o library.so library.go'.format(
        installation_dir))


@operation
def execute_call(ctx, **kwargs):
    resource_config = ctx.node.properties.get('resource_config', {})
    go_function = resource_config.get('go_function', '')
    go_function_inputs = resource_config.get('go_function_inputs', [])
    go_function_outputs = resource_config.get('go_function_outputs', [])
    installation_dir = '/tmp/go_stuff'
    libraray_path = "{0}/library.so".format(installation_dir)

    import ctypes
    library = ctypes.cdll.LoadLibrary(libraray_path)
    function = getattr(library, go_function)
    function.restype = ctypes.c_void_p
    function_output = function()
    function_out_bytes = ctypes.string_at(function_output)
    function_string = function_out_bytes.decode('utf-8')
    ctx.logger.info('{0}'.format(function_string))

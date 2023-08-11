import os
import io
import py
import sys
import tempfile
import subprocess

from cloudify.decorators import operation
from cloudify_common_sdk.utils import download_file

@operation
def install_go(ctx, **kwargs):
    resource_config = ctx.node.properties.get('resource_config', {})
    go_version = resource_config.get('go_version', '')
    temp_dir = tempfile.mkdtemp()
    installation_dir = '{0}/go.tar.gz'.format(temp_dir)

    installation_source = "https://dl.google.com/go/go{0}.linux-amd64.tar.gz".format(go_version)
    download_file(installation_dir, installation_source)
    subprocess.check_output(['cd {0} && tar -xvf {1}'.format(temp_dir, 'go.tar.gz')], shell=True)
    ctx.instance.runtime_properties['go_setup'] = temp_dir


@operation
def compile_code(ctx, **kwargs):
    resource_config = ctx.node.properties.get('resource_config', {})
    go_source_code = resource_config.get('go_source_code', '')
    installation_dir = ctx.instance.runtime_properties['go_setup']

    with open('{0}/library.go'.format(installation_dir), 'w') as f:
        f.write(go_source_code)

    subprocess.check_output(['cd {0} && CGO_ENABLED=1 {0}/go/bin/go build -buildmode=c-shared -o library.so library.go'.format(
        installation_dir)], shell=True)


@operation
def execute_call(ctx, **kwargs):
    resource_config = ctx.node.properties.get('resource_config', {})
    go_function = resource_config.get('go_function', '')
    go_function_inputs = resource_config.get('go_function_inputs', [])
    go_function_output = resource_config.get('go_function_output', [])
    installation_dir = ctx.instance.runtime_properties['go_setup']
    libraray_path = "{0}/library.so".format(installation_dir)

    import ctypes
    library = ctypes.cdll.LoadLibrary(libraray_path)
    function = getattr(library, go_function)
    finputs = []
    if go_function_inputs:
        argtypes = []
        for finput in go_function_inputs:
            argtypes.append(getattr(ctypes, finput.get('argtype')) )
            value = finput.get('value')
            if finput.get('argtype') == 'c_char_p':
                value.encode('uft-8')
            finputs.append(value)
    if go_function_output:
        function.restype = getattr(ctypes, go_function_output.get('restype'))
        function_output = function()
        function_out_bytes = ctypes.string_at(function_output)
        function_string = function_out_bytes.decode('utf-8')
        ctx.logger.info('{0}'.format(function_string))
    else:
        if finputs:
            function(finputs)
        else:
            capture = py.io.StdCaptureFD(out=False, in_=False)
            function()
            out,err = capture.reset()
            ctx.logger.info('OUT: {0}, ERR: {1}'.format(out, err))


@operation
def cleanup(ctx, **kwargs):
    installation_dir = ctx.instance.runtime_properties['go_setup']
    os.remove(installation_dir)

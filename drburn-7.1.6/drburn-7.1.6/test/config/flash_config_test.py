from argparse import Namespace
from pathlib import PosixPath

from config.flash_config import FlashConfig


class TestFlashConfig:
    def test_parse_default_config(self):
        # Given
        namespace = Namespace(adaptive_adaptive=None, adaptive_persistency=None, adaptive_source=None,
                              adaptive_stub_libs=None, artifactory_password=None, artifactory_uri=None,
                              artifactory_user=None, bundle_source=None, clear_adaptive_persistency=True, config=None,
                              ddu_script='/lhome/pflorek/projects/drburn/src/flashing/ddu/flash_ddu.sh',
                              ddu_source=None, debug=False, download=False, idc_ip='10.121.1.50', idc_port=22,
                              interactive=True, non_interactive=False, modules={}, ndas_source=None,
                              output_localstorage=PosixPath('/lhome/pflorek/Downloads/drburn'),
                              output_logdir=PosixPath('/lhome/pflorek/.config/drburn'),
                              output_workspace=PosixPath('/tmp/drburn/2023-06-15_10-13-47-976224'), rrdata_source=None,
                              update_adaptive=False, update_bundle=False, update_ddu=False, update_ndas=False,
                              update_rrdata=False, verbose=False)

        expected = FlashConfig.construct(
            **{'config': None, 'debug': False, 'download': False, 'interactive': True, 'verbose': False,
               'output': {'logdir': PosixPath('/lhome/pflorek/.config/drburn'),
                          'localstorage': PosixPath('/lhome/pflorek/Downloads/drburn'),
                          'workspace': PosixPath('/tmp/drburn/2023-06-15_10-13-47-976224')},
               'artifactory': {'uri': None, 'user': None, 'password': None}, 'idc': {'ip': '10.121.1.50', 'port': 22},
               'modules': {
                   'adaptive': {'id': 'adaptive', 'update': False, 'clear_persistency': True,
                                'sources': {'source': {'error': False, 'url': None}}},
                   'ndas': {'id': 'ndas', 'update': False, 'sources': {'source': {'error': False, 'url': None}}},
                   'rrdata': {'id': 'rrdata', 'update': False, 'sources': {'source': {'error': False, 'url': None}}},
                   'ddu': {'aurix_port': None,
                       'clear_persistency': False, 'id': 'ddu', 'update': False, 'sources': {
                       'source': {'error': False, 'url': None},
                       'script': {'error': False,
                                  'url': PosixPath('/lhome/pflorek/projects/drburn/src/flashing/ddu/flash_ddu.sh')}}
                           },
                   'bundle': {'id': 'bundle', 'update': False, 'sources': {'source': {'error': False, 'url': None}}}}})

        # When
        actual = FlashConfig.from_args(namespace)

        # Then
        assert actual.dict() == expected.dict()

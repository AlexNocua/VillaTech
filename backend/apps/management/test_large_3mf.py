from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
from unittest.mock import patch
from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from .mesh_preview import mesh_preview,parse_3mf_xml
from .test_models_mail import NS,MESH

class LargeThreeMFTests(SimpleTestCase):
    def model_xml(self):
        return f'<model xmlns="{NS}"><resources><object id="1">{MESH}</object></resources><build><item objectid="1"/></build></model>'.encode()
    def test_unrelated_80mb_metadata_does_not_block_preview(self):
        data=BytesIO()
        with ZipFile(data,'w',ZIP_DEFLATED) as z:
            z.writestr('3D/3dmodel.model',self.model_xml())
            with z.open('Metadata/slicer.data','w') as file:
                for _ in range(80):file.write(b'0'*1024*1024)
        self.assertEqual(mesh_preview(SimpleUploadedFile('large.3mf',data.getvalue()))['count'],1)
    def test_actual_geometry_xml_over_old_16mb_limit(self):
        vertices='<vertices><vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/><vertex x="0" y="1" z="0"/></vertices>'
        xml=(f'<model xmlns="{NS}"><resources><object id="1"><mesh>{vertices}<triangles>'.encode()
             +b'<triangle v1="0" v2="1" v3="2"/>'*600000
             +b'</triangles></mesh></object></resources><build><item objectid="1"/></build></model>')
        self.assertGreater(len(xml),16*1024*1024)
        class BoundedStream(BytesIO):
            def read(self,size=-1):
                if size<0 or size>65536:raise AssertionError('Whole XML read attempted')
                return super().read(size)
        model=parse_3mf_xml(BoundedStream(xml),[0])
        self.assertEqual(len(model['objects']['1']['indices']),1800000)
    def test_memory_budget_still_limits_geometry(self):
        with patch('apps.management.mesh_preview.MAX_GEOMETRY_BYTES',20):
            with self.assertRaises(ValidationError):parse_3mf_xml(BytesIO(self.model_xml()),[0])
    def test_dtd_is_rejected_even_when_streamed(self):
        xml=b'<!DOCTYPE model [<!ENTITY x "data">]><model><metadata>&x;</metadata></model>'
        with self.assertRaises(ValidationError):parse_3mf_xml(BytesIO(xml),[0])
    def test_geometry_budget_ignores_metadata_text(self):
        xml=self.model_xml().replace(b'<resources>',b'<metadata name="test">'+b'abc'*1000000+b'</metadata><resources>')
        budget=[0];model=parse_3mf_xml(BytesIO(xml),budget)
        self.assertEqual(budget[0],84);self.assertEqual(len(model['build']),1)

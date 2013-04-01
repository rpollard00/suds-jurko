# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jurko Gospodnetić ( jurko.gospodnetic@pke.hr )

"""
Unit tests related to Suds Python library reply processing.

Implemented using the 'pytest' testing framework.

"""

if __name__ == "__main__":
    try:
        import pytest
        pytest.main(["--pyargs", __file__])
    except ImportError:
        print("'py.test' unit testing framework not available. Can not run "
            "'%s' directly as a script." % (__file__,))
    import sys
    sys.exit(-2)


import suds
import tests

import pytest

import httplib
import xml.sax


def test_ACCEPTED_and_NO_CONTENT_status_reported_as_None_with_faults():
    client = tests.client_from_wsdl(_wsdl__simple, faults=True)
    f = lambda r, s : client.service.f(__inject={"reply":suds.byte_str(r),
        "status":s})
    assert f("", None) is None
    pytest.raises(Exception, f, "", httplib.INTERNAL_SERVER_ERROR)
    assert f("", httplib.ACCEPTED) is None
    assert f("", httplib.NO_CONTENT) is None
    assert f("bla-bla", httplib.ACCEPTED) is None
    assert f("bla-bla", httplib.NO_CONTENT) is None


def test_ACCEPTED_and_NO_CONTENT_status_reported_as_None_without_faults():
    client = tests.client_from_wsdl(_wsdl__simple, faults=False)
    f = lambda r, s : client.service.f(__inject={"reply":suds.byte_str(r),
        "status":s})
    assert f("", None) is not None
    assert f("", httplib.INTERNAL_SERVER_ERROR) is not None
    assert f("", httplib.ACCEPTED) is None
    assert f("", httplib.NO_CONTENT) is None
    assert f("bla-bla", httplib.ACCEPTED) is None
    assert f("bla-bla", httplib.NO_CONTENT) is None


def test_badly_formed_reply_XML():
    for faults in (True, False):
        client = tests.client_from_wsdl(_wsdl__simple, faults=faults)
        pytest.raises(xml.sax.SAXParseException, client.service.f,
            __inject={"reply":suds.byte_str("bad food")})


def test_empty_reply():
    client = tests.client_from_wsdl(_wsdl__simple, faults=False)
    f = lambda status=None, description=None : client.service.f(__inject=dict(
        reply=suds.byte_str(), status=status, description=description))
    status, reason = f()
    assert status == httplib.OK
    assert reason is None
    status, reason = f(httplib.OK)
    assert status == httplib.OK
    assert reason is None
    status, reason = f(httplib.INTERNAL_SERVER_ERROR)
    assert status == httplib.INTERNAL_SERVER_ERROR
    assert reason == 'injected reply'
    status, reason = f(httplib.FORBIDDEN)
    assert status == httplib.FORBIDDEN
    assert reason == 'injected reply'
    status, reason = f(httplib.FORBIDDEN, "kwack")
    assert status == httplib.FORBIDDEN
    assert reason == 'kwack'


def test_fault_reply_with_unicode_faultstring():
    unicode_string = u"€ Jurko Gospodnetić ČĆŽŠĐčćžšđ"
    fault_xml = suds.byte_str(u"""\
<?xml version="1.0"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <env:Fault>
      <faultcode>env:Client</faultcode>
      <faultstring>%s</faultstring>
    </env:Fault>
  </env:Body>
</env:Envelope>
""" % unicode_string)

    client = tests.client_from_wsdl(_wsdl__simple, faults=True)
    try:
        client.service.f(__inject=dict(reply=fault_xml,
            status=httplib.INTERNAL_SERVER_ERROR))
    except suds.WebFault, e:
        e.fault.faultstring = unicode_string
        assert e.document.__class__ is suds.sax.document.Document
    else:
        pytest.fail("Expected WebFault exception not raised.")

    client = tests.client_from_wsdl(_wsdl__simple, faults=False)
    status, fault = client.service.f(__inject=dict(reply=fault_xml,
        status=httplib.INTERNAL_SERVER_ERROR))
    assert status == httplib.INTERNAL_SERVER_ERROR
    assert fault.faultstring == unicode_string


def test_invalid_fault_namespace():
    fault_xml = suds.byte_str("""\
<?xml version="1.0"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/" xmlns:p="x">
  <env:Body>
    <p:Fault>
      <faultcode>env:Client</faultcode>
      <faultstring>Dummy error.</faultstring>
      <detail>
        <errorcode>ultimate</errorcode>
      </detail>
    </p:Fault>
  </env:Body>
</env:Envelope>
""")
    client = tests.client_from_wsdl(_wsdl__simple, faults=False)
    try:
        client.service.f(__inject=dict(reply=fault_xml, status=httplib.OK))
    except Exception, e:
        assert e.__class__ is Exception
        assert str(e) == "<faultcode/> not mapped to message part"
    else:
        pytest.fail("Expected Exception not raised.")

    for http_status in (httplib.INTERNAL_SERVER_ERROR,
        httplib.PAYMENT_REQUIRED):
        status, reason = client.service.f(__inject=dict(reply=fault_xml,
            status=http_status, description="trla baba lan"))
        assert status == http_status
        assert reason == "trla baba lan"


def test_missing_wrapper_response():
    """
    Suds library's automatic structure unwrapping should not be applied to
    interpreting received SOAP Response XML.

    """
    client = tests.client_from_wsdl(_wsdl("""\
      <xsd:element name="Wrapper">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="fResponse" type="xsd:string" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>""", "Wrapper"))
    assert _isOutputWrapped(client, "f")

    response_with_missing_wrapper = client.service.f(__inject=dict(
        reply=suds.byte_str("""<?xml version="1.0"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <fResponse xmlns="my-namespace">Anything</fResponse>
  </env:Body>
</env:Envelope>""")))
    assert response_with_missing_wrapper is None


def test_reply_error_with_detail_with_fault():
    client = tests.client_from_wsdl(_wsdl__simple, faults=True)

    for http_status in (httplib.OK, httplib.INTERNAL_SERVER_ERROR):
        try:
            client.service.f(__inject=dict(reply=_fault_reply__with_detail,
                status=http_status))
        except suds.WebFault, e:
            _test_fault(e.fault, True)
            assert e.document.__class__ is suds.sax.document.Document
            assert str(e) == "Server raised fault: 'Dummy error.'"
        else:
            pytest.fail("Expected exception suds.WebFault not raised.")

    try:
        client.service.f(__inject=dict(reply=_fault_reply__with_detail,
            status=httplib.BAD_REQUEST, description="quack-quack"))
    except Exception, e:
        assert e.__class__ is Exception
        assert e.args[0][0] == httplib.BAD_REQUEST
        assert e.args[0][1] == "quack-quack"
    else:
        pytest.fail("Expected Exception not raised.")


def test_reply_error_with_detail_without_fault():
    client = tests.client_from_wsdl(_wsdl__simple, faults=False)

    for http_status in (httplib.OK, httplib.INTERNAL_SERVER_ERROR):
        status, fault = client.service.f(__inject=dict(
            reply=_fault_reply__with_detail, status=http_status))
        assert status == httplib.INTERNAL_SERVER_ERROR
        _test_fault(fault, True)

    status, fault = client.service.f(__inject=dict(
        reply=_fault_reply__with_detail, status=httplib.BAD_REQUEST))
    assert status == httplib.BAD_REQUEST
    assert fault == "injected reply"

    status, fault = client.service.f(__inject=dict(
        reply=_fault_reply__with_detail, status=httplib.BAD_REQUEST,
        description="haleluja"))
    assert status == httplib.BAD_REQUEST
    assert fault == "haleluja"


def test_reply_error_without_detail_with_fault():
    client = tests.client_from_wsdl(_wsdl__simple, faults=True)

    for http_status in (httplib.OK, httplib.INTERNAL_SERVER_ERROR):
        try:
            client.service.f(__inject=dict(reply=_fault_reply__without_detail,
                status=http_status))
        except suds.WebFault, e:
            _test_fault(e.fault, False)
            assert e.document.__class__ is suds.sax.document.Document
            assert str(e) == "Server raised fault: 'Dummy error.'"
        else:
            pytest.fail("Expected exception suds.WebFault not raised.")

    try:
        client.service.f(__inject=dict(reply=_fault_reply__with_detail,
            status=httplib.BAD_REQUEST, description="quack-quack"))
    except Exception, e:
        assert e.__class__ is Exception
        assert e.args[0][0] == httplib.BAD_REQUEST
        assert e.args[0][1] == "quack-quack"
    else:
        pytest.fail("Expected Exception not raised.")


def test_reply_error_without_detail_without_fault():
    client = tests.client_from_wsdl(_wsdl__simple, faults=False)

    for http_status in (httplib.OK, httplib.INTERNAL_SERVER_ERROR):
        status, fault = client.service.f(__inject=dict(
            reply=_fault_reply__without_detail, status=http_status))
        assert status == httplib.INTERNAL_SERVER_ERROR
        _test_fault(fault, False)

    status, fault = client.service.f(__inject=dict(
        reply=_fault_reply__without_detail, status=httplib.BAD_REQUEST,
        description="kung-fu-fui"))
    assert status == httplib.BAD_REQUEST
    assert fault == "kung-fu-fui"


def test_simple_bare_and_wrapped_output():
    # Prepare web service proxies.
    client_bare = tests.client_from_wsdl(_wsdl("""\
      <xsd:element name="fResponse" type="xsd:string" />""", "fResponse"))
    client_wrapped = tests.client_from_wsdl(_wsdl("""\
      <xsd:element name="Wrapper">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="fResponse" type="xsd:string" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>""", "Wrapper"))

    #   Make sure suds library inteprets our WSDL definitions as wrapped or
    # bare output interfaces as expected.
    assert not _isOutputWrapped(client_bare, "f")
    assert _isOutputWrapped(client_wrapped, "f")

    #   Both bare & wrapped single parameter output web service operation
    # results get presented the same way even though the wrapped one actually
    # has an extra wrapper element around its received output data.
    data = "The meaning of life."
    get_response = lambda client, x : client.service.f(__inject=dict(
        reply=suds.byte_str(x)))

    response_bare = get_response(client_bare, """<?xml version="1.0"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <fResponse xmlns="my-namespace">%s</fResponse>
  </env:Body>
</env:Envelope>""" % data)
    assert response_bare.__class__ is suds.sax.text.Text
    assert response_bare == data

    response_wrapped = get_response(client_wrapped, """<?xml version="1.0"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <Wrapper xmlns="my-namespace">
      <fResponse>%s</fResponse>
    </Wrapper>
  </env:Body>
</env:Envelope>""" % data)
    assert response_wrapped.__class__ is suds.sax.text.Text
    assert response_wrapped == data


def test_wrapped_sequence_output():
    client = tests.client_from_wsdl(_wsdl("""\
      <xsd:element name="Wrapper">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="result1" type="xsd:string" />
            <xsd:element name="result2" type="xsd:string" />
            <xsd:element name="result3" type="xsd:string" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>""", "Wrapper"))
    assert _isOutputWrapped(client, "f")

    response = client.service.f(__inject=dict(reply=suds.byte_str("""\
<?xml version="1.0"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <Wrapper xmlns="my-namespace">
        <result1>Uno</result1>
        <result2>Due</result2>
        <result3>Tre</result3>
    </Wrapper>
  </env:Body>
</env:Envelope>""")))

    #   Composite replies always get unmarshalled as a dynamically constructed
    # class named 'reply'.
    assert len(response.__class__.__bases__) == 1
    assert response.__class__.__name__ == "reply"
    assert response.__class__.__bases__[0] is suds.sudsobject.Object

    # Check response content.
    assert len(response) == 3
    assert response.result1 == "Uno"
    assert response.result2 == "Due"
    assert response.result3 == "Tre"
    assert response.result1.__class__ is suds.sax.text.Text
    assert response.result2.__class__ is suds.sax.text.Text
    assert response.result3.__class__ is suds.sax.text.Text


def _attibutes(object):
    result = set()
    for x in object:
        result.add(x[0])
    return result


def _isOutputWrapped(client, method_name):
    assert len(client.wsdl.bindings) == 1
    operation = client.wsdl.bindings.values()[0].operations[method_name]
    return operation.soap.output.body.wrapped


def _test_fault(fault, has_detail):
    assert fault.faultcode == "env:Client"
    assert fault.faultstring == "Dummy error."
    assert hasattr(fault, "detail") == has_detail
    assert not has_detail or fault.detail.errorcode == "ultimate"
    assert not hasattr(fault, "nonexisting")
    expected_attributes = set(("faultcode", "faultstring"))
    if has_detail:
        expected_attributes.add("detail")
    assert _attibutes(fault) == expected_attributes
    assert not has_detail or _attibutes(fault.detail) == set(("errorcode",))


def _wsdl(schema_content, *args):
    """
      Returns a WSDL schema used in different tests throughout this test
    module.

      The first input parameter is the schema part of the WSDL, the rest of the
    parameters identify top level input parameter elements.

"""
    wsdl = ["""\
<?xml version='1.0' encoding='UTF-8'?>
<wsdl:definitions targetNamespace="my-namespace"
xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
xmlns:ns="my-namespace"
xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
  <wsdl:types>
    <xsd:schema targetNamespace="my-namespace"
    elementFormDefault="qualified"
    attributeFormDefault="unqualified"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema">
%s
    </xsd:schema>
  </wsdl:types>
  <wsdl:message name="fResponseMessage">""" % schema_content]

    assert len(args) >= 1
    for arg in args:
        wsdl.append("""\
    <wsdl:part name="parameters" element="ns:%s" />""" % arg)

    wsdl.append("""\
  </wsdl:message>
  <wsdl:portType name="dummyPortType">
    <wsdl:operation name="f">
      <wsdl:output message="ns:fResponseMessage" />
    </wsdl:operation>
  </wsdl:portType>
  <wsdl:binding name="dummy" type="ns:dummyPortType">
    <soap:binding style="document"
    transport="http://schemas.xmlsoap.org/soap/http" />
    <wsdl:operation name="f">
      <soap:operation soapAction="f" style="document" />
      <wsdl:output><soap:body use="literal" /></wsdl:output>
    </wsdl:operation>
  </wsdl:binding>
  <wsdl:service name="dummy">
    <wsdl:port name="dummy" binding="ns:dummy">
      <soap:address location="unga-bunga-location" />
    </wsdl:port>
  </wsdl:service>
</wsdl:definitions>
""")

    return suds.byte_str("\n".join(wsdl))


_fault_reply__with_detail = suds.byte_str("""\
<?xml version="1.0"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <env:Fault>
      <faultcode>env:Client</faultcode>
      <faultstring>Dummy error.</faultstring>
      <detail>
        <errorcode>ultimate</errorcode>
      </detail>
    </env:Fault>
  </env:Body>
</env:Envelope>
""")

_fault_reply__without_detail = suds.byte_str("""\
<?xml version="1.0"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <env:Fault>
      <faultcode>env:Client</faultcode>
      <faultstring>Dummy error.</faultstring>
    </env:Fault>
  </env:Body>
</env:Envelope>
""")

_wsdl__simple = _wsdl("""\
      <xsd:element name="fResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="output_i" type="xsd:integer" />
            <xsd:element name="output_s" type="xsd:string" />
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>""", "fResponse")

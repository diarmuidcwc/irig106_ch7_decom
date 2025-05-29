from setuptools import setup

setup(
    name="irig106_ch7_decom",
    version="0.3",
    author="Diarmuid Collins",
    author_email="dcollins@curtisswright.com",
    url="https://github.com/diarmuidcwc/irig107_ch7_decom.git",
    description="Generate ch7 packetizer packets and decom them",
    packages=["src"],
    install_requires=["AcraNetwork>=1.2.5"],
    python_requires=">3.10.0",
    scripts=["scripts/pcm_pktizer_ch7_decom.py", "scripts/tx_ch7_pktizer.py", "scripts/test_xml_parse.py"],
)

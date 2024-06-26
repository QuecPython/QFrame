## Serial Port and TCP Server Relay Demo  

This routine test uses the QFrame framework to implement a simple data transmission between a serial port and a TCP server.

Pre preparation：

1. Download the source code of QFrame: `https://github.com/QuecPython/QFrame.git`
2. Download the source code to the module's `usr` directory
3. coding `demo.py` (Example source code can be found in the following text)
4. running`demo.py`

source code in `demo.py` as below:

```python
# demo.py

import checkNet
from usr.qframe import Application, CurrentApp
from usr.qframe import TcpClient, Uart
from usr.qframe.logging import getLogger

logger = getLogger(__name__)


PROJECT_NAME = 'Sample DTU'
PROJECT_VERSION = '1.0.0'

def poweron_print_once():
    checknet = checkNet.CheckNetwork(
        PROJECT_NAME,
        PROJECT_VERSION,
    )
    checknet.poweron_print_once()
    
    
class BusinessClient(TcpClient):

    def recv_callback(self, data):
        """implement this method to handle data received from tcp server

        :param data: data bytes received from tcp server
        :return:
        """
        logger.info('recv data from tcp server, then post to uart')
        CurrentApp().uart.write(data)
        
        
class UartService(Uart):

    def recv_callback(self, data):
        """implement this method to handle data received from UART

        :param data: data bytes received from UART
        :return:
        """
        logger.info('read data from uart, then post to tcp server')
        CurrentApp().client.send(data)
        
        
def create_app(name='DTU', config_path='/usr/dev.json'):
    # init application
    _app = Application(name)
    # read settings from json file
    _app.config.from_json(config_path)

    # init business tcp client
    client = BusinessClient('client')
    client.init_app(_app)

    # init business uart
    uart = UartService('uart')
    uart.init_app(_app)

    return _app


app = create_app()


if __name__ == '__main__':
    poweron_print_once()
    app.mainloop()
```

> NOTICE: In this routine test, `from usr. qframe import <xxx>`  indicates that we imported the various functional modules of `qframe` from the `usr` directory.


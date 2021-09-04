'use strict';

var Transport = require('azure-iot-device-mqtt').Mqtt;
var Client = require('azure-iot-device').ModuleClient;
var Message = require('azure-iot-device').Message;
let app = require('express')();
let http = require('http').createServer(app);
let io = require('socket.io')(http);

io.on('connection', (socket) => {
  console.log('USER CONNECTED');

  socket.on('disconnect', function () {
    console.log('USER DISCONNECTED');
  });

});

app.get('/',(req,res)=>{
  console.info(req);
  console.info(res);
  res.send('Hello World- From Edge Node js server')
});

http.listen(8092, () => {

  console.info('started server on port - 8092');

  //Iot device mqtt connection  
  Client.fromEnvironment(Transport, function (err, client) {
    if (err) {
      throw err;
    } else {
      client.on('error', function (err) {
        throw err;
      });

      // connect to the Edge instance
      client.open(function (err) {
        if (err) {
          throw err;
        } else {
          console.log('IoT Hub module client initialized');

          // Act on input messages to the module.
          client.on('inputMessage', function (inputName, msg) {
            pipeMessage(client, inputName, msg);
          });
        }
      });
    }
  });

});

// This function just pipes the messages without any change.
function pipeMessage(client, inputName, msg) {
  client.complete(msg, printResultFor('Receiving message'));

  if (inputName === 'input1') {
    var message = msg.getBytes().toString('utf8');
    if (message) {
      //var outputMsg = new Message(message);
      // client.sendOutputEvent('output1', outputMsg, printResultFor('Sending received message'));
      //Sending the data to client web app (emit data)
      io.emit('bmsWebApp', { x: (new Date()).getTime(), y: message });
      //console.log(message)
      console.log('new value emmited ;-)')
    }
  }
}

// Helper function to print results in the console
function printResultFor(op) {
  return function printResult(err, res) {
    if (err) {
      console.log(op + ' error: ' + err.toString());
    }
    if (res) {
      console.log(op + ' status: ' + res.constructor.name);
    }
  };
}

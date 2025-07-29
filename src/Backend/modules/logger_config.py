import logging
import datetime
from flask_socketio import SocketIO
import os

# Define the SocketIO instance
socketio = None  # This will be set later

# Custom log level for STATUS
STATUS_LEVEL_NUM = 25
logging.addLevelName(STATUS_LEVEL_NUM, "STATUS")

def status(self, message, *args, **kwargs):
    if self.isEnabledFor(STATUS_LEVEL_NUM):
        self._log(STATUS_LEVEL_NUM, message, args, **kwargs)

# Add the method to the logging.Logger class

# normal logs like errors go to files but status logs goes to the front end
logging.Logger.status = status

# delivery person for STATUS logs
# when a status logg is created it this handler sends it over socket io to the front end 
class WebSocketHandler(logging.Handler):

    def emit(self, record):
        # Only send `STATUS` level logs to the frontend
        if record.levelno == STATUS_LEVEL_NUM:
            msg = self.format(record)
            try:
                if socketio:
                    socketio.emit('log_message', {'message': msg})
                    print("log emitted", flush=True)
                else:
                    print("SocketIO instance not set, cannot emit logs", flush=True)
            except Exception as e:
                print(f"Failed to emit log over WebSocket: {e}")

class ExcludeRsyncFilter(logging.Filter):
    def filter(self, record):
        # Exclude logs that contain "rsync" Why? To avoid cluttering the frontend with boring technical logs.
        return "rsync" not in record.getMessage()

# Logger configuration # newsroom
def setup_logging(sio_instance):
    global socketio
    socketio = sio_instance # making an instance of the socket.io instance
    # it like giving a direct phone line from the website to the news room

    log_dir = "../../../LOGS_DOBBY"
    os.makedirs(log_dir, exist_ok=True) # making sure the logs directory exists

    # Get the current date and time for the log filename
    # it creates a seperate log file for each run of the app
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"../../LOGS/logs_{current_datetime}.txt"
    status_log_file = f"../../LOGS/status_logs_{current_datetime}.txt"

    # Set up basic logging
    # first this first start loging from the debug and in format of time loglevel(INFO, ERROR) to msg in the main log
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        filename=output_file)

    # Define a StreamHandler to print log messages to the console
    console_handler = logging.StreamHandler() 
    console_handler.setLevel(logging.INFO) #Sets up a handler to print log messages to your terminal/console.
    formatter = logging.Formatter('%(message)s') #Only shows INFO and above (not DEBUG, to avoid clutter).
    console_handler.setFormatter(formatter) # Uses a simple format (just the message, no timestamps).

    # Add a file handler specifically for STATUS logs
    status_file_handler = logging.FileHandler(status_log_file) #Creates a special file just for STATUS logs (your custom level)
    status_file_handler.setLevel(STATUS_LEVEL_NUM) #Only logs messages at the STATUS level (not regular INFO/ERROR).
    status_file_handler.setFormatter(formatter) #Keeps these logs in a separate file for easy review.

    # Add the WebSocketHandler
    ws_handler = WebSocketHandler() #This is your “live broadcaster.”
    ws_handler.setLevel(STATUS_LEVEL_NUM)  # Only STATUS level logs will be pushed
    ws_handler.setFormatter(formatter) #When a STATUS log is created, this handler sends it through Socket.IO to the frontend (website) in real time.

    # Set up the root logger #Adds all your handlers to the main logger.
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(status_file_handler)  # Add STATUS file handler
    root_logger.addHandler(ws_handler)  # Add the WebSocket handler
    """
    Now, when a log message is created, it gets sent to the right places:

        Console (for you to see)

        File (for records)

        Frontend (for users to see live)
    """
    #Adds a filter to each handler to ignore messages containing “rsync.”
    #Keeps your logs clean and relevant.
    console_handler.addFilter(ExcludeRsyncFilter())
    status_file_handler.addFilter(ExcludeRsyncFilter())
    ws_handler.addFilter(ExcludeRsyncFilter())

    # Set werkzeug logging level
    # werkzeug_log = logging.getLogger('werkzeug')
    # werkzeug_log.setLevel(logging.WARNING)

# Usage of custom `STATUS` log level
# Example: logger.status("This is a custom status log")

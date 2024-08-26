import socket
import threading
import socketserver
import time
import sys
import json
import zlib
import datetime
import os

# todo: hex in form 0xFFFF is accepted, although not specified

GLOBAL_CONFIG = { \
    'host': 'localhost', \
    'port': 50600, \
    'nl_sequence': '\r\n', \
    'error_codes': True, \
    'error_messages': True, \
    'stap_version': '834.8', \
    'max_input_buffer': 1024, \
    'max_transmitex_words': 1023, \
    'data_generator_interval': 5.0, \
    'data_generator_word_delay': 0.05, \
    
    'equipment': { \
        0: [ 'a429rx', 'high' ], \
        1: [ 'a429rx', 'low' ], \
        2: [ 'a429rx', 'unknown' ], \
        10: [ 'a429tx', 'high', 'free' ], \
        11: [ 'a429tx', 'low', 'owned' ], \
        12: [ 'a429tx', 'high', 'locked' ], \
        20: [ 'a717rx', 1024 ], \
        21: [ 'a717rx', 2048 ], \
        30: [ 'disc', 'in' ], \
        31: [ 'disc', 'out' ], \
        32: [ 'disc', 'out', 'free' ], \
        33: [ 'disc', 'out', 'owned' ], \
        34: [ 'disc', 'out', 'locked' ] }, \
    
    'sample_data': { \
        # examples from A429 attachment 6, table 6-25 (label 21 selected EPR, but N1 skipped)
        0o001: 0x09d410, \
        0o002: 0x0514c0, \
        0o003: 0x089580, \
        0o012: 0x019400, \
        0o013: 0x059540, \
        0o020: 0x688000, \
        0o021: 0x081400, \
        0o022: 0x021400, \
        0o023: 0x05dc00, \
        0o024: 0x095000, \
        0o025: 0x104000, \
        0o026: 0x108c00, \
        0o125: 0x055154, \
        0o165: 0x091414, \
        0o170: 0x080000, \
        0o201: 0x095e18, \
        0o230: 0x159400, \
        0o231: 0x609400, \
        0o232: 0x654940, \
        0o233: 0x004c00, \
        0o235: 0x0a6480, \
        
        # examples from A429 attachment 6, table 6-27
        0o100: 0x600000, \
        0o101: 0x6d5500, \
        0o102: 0x6a0280, \
        0o103: 0x6d3800, \
        0o104: 0x7dd800, \
        0o106: 0x632000, \
        0o114: 0x787200, \
        0o116: 0x666000, \
        0o117: 0x64b000, \
        0o140: 0x62ab00, \
        0o141: 0x7f1c00, \
        0o142: 0x678000, \
        0o150: 0x6972a0, \
        0o164: 0x64c900, \
        0o173: 0x60d800, \
        0o174: 0x7d8000, \
        0o202: 0x680ee0, \
        0o203: 0x657e40, \
        0o205: 0x634080, \
        0o206: 0x66a400, \
        0o210: 0x646a00, \
        0o213: 0x606800, \
        0o211: 0x7f3800, \
        0o212: 0x788e00, \
        0o310: 0x673ea8, \
        0o311: 0x7716c0, \
        0o312: 0x628a00, \
        0o323: 0x6a0500 }, \
    
}

GLOBAL_ERRORS = { \
    'UNKNOWN_COMMAND': [ 404, 'Unknown command' ], \

    'INV_ARG_NO': [ 411, 'Invalid number of arguments' ], \
    'INV_CHANNEL_FORMAT': [ 412, 'Invalid channel ID format' ], \
    'INV_FREQ_FORMAT': [ 413, 'Invalid frequency format' ], \
    'INV_FREQUENCY_RANGE': [ 414, 'Frequency out of range' ], \
    'INV_LABEL_FORMAT': [ 415, 'Invalid label format' ], \
    'INV_LABEL_RANGE': [ 416, 'Label out of range' ], \
    'INV_SUBFRAME_FORMAT': [ 417, 'Unknown subframe no. format' ], \
    'INV_SUFRAME_RANGE': [ 418, 'Subframe no. out of range' ], \
    'INV_WORD_FORMAT': [ 419, 'Unknown word no. format' ], \
    'INV_WORD_RANGE': [ 420, 'Word no. out of range' ], \
    'INV_DATA_FORMAT': [ 421, 'Unknown data format' ], \
    'INV_DATA_RANGE': [ 422, 'Data out of range' ], \
    'INV_STATE_VALUE': [ 423, 'Invalid state value' ], \
    'INV_WORDCOUNT_FORMAT': [ 424, 'Unknown format of number of words' ], \
    'INV_WORDCOUNT_RANGE': [ 425, 'Number of words out of range' ], \
    'INV_CHECKSUM_MODE': [ 426, 'Unsupported checksum mode' ], \
    'INV_CRC32_MODE': [ 427, 'Unsupported CRC32 mode' ], \
    'CHECKSUM_MISSING': [ 428, 'Checksum value missing' ], \
    'INV_CHECKSUM_FORMAT': [ 429, 'Unknown checksum format' ], \
    'INV_CHECKSUM_VALUE': [ 430, 'Invalid checksum value' ], \

    'LABEL_ALREADY_SUBS': [ 441, 'Label already subscribed' ], \
    'LABEL_NOT_SUBS': [ 442, 'Label not subscribed' ], \
    'WORD_ALREADY_SUBS': [ 443, 'Word already subscribed' ], \
    'WORD_NOT_SUBS': [ 444, 'Word not subscribed' ], \
    'DISC_ALREADY_SUBS': [ 445, 'Discrete line already subscribed' ], \
    'DISC_NOT_SUBS': [ 446, 'Discrete line not subscribed' ], \

    'CHANNEL_NOT_FOUND': [ 461, 'Channel not found' ], \
    'INV_CHANNEL_TYPE_OUTPUT': [ 462, 'Channel is not an output' ], \
    'INV_CHANNEL_TYPE_A429TX': [ 463, 'Channel is not an A429 transmitter' ], \
    'INV_CHANNEL_TYPE_DISC': [ 464, 'Channel is not a discrete line' ], \
    'INV_CHANNEL_TYPE_DISC_IN': [ 465, 'Channel is not a discrete input' ], \
    'INV_CHANNEL_TYPE_DISC_OUT': [ 466, 'Channel is not a discrete output' ], \

    'GENERIC_UNSUPPORTED': [ 501, 'Generic parameter not available' ], \
    'UNKNOWN_ERROR': [ 500, 'Some other error' ] \
}

class Logger():
    def debug(message: str):
        print(datetime.datetime.now(), threading.current_thread().name, message)

    def info(message: str):
        print(datetime.datetime.now(), threading.current_thread().name, message)

    def error(message: str):
        print(datetime.datetime.now(), threading.current_thread().name, message, file=sys.stderr)

class STAPHandler(socketserver.BaseRequestHandler):
    def get_ts():
        return int(time.monotonic() * 1000)
    
    def get_err(id: str):
        if GLOBAL_CONFIG['error_codes'] and id in GLOBAL_ERRORS:
            if GLOBAL_CONFIG['error_messages']:
                return 'err,{},{}'.format(GLOBAL_ERRORS[id][0], GLOBAL_ERRORS[id][1]).encode('ascii')
            else:
                return 'err,{}'.format(GLOBAL_ERRORS[id][0]).encode('ascii')
        else:
            return b'err'
    
    def get_crc_bytes(data):
        return ',{:08x}'.format((zlib.crc32(data + b','))).encode('ascii')
        
    def data_generator(self, client):
        Logger.info('Data generator for the client {}:{} starts.'.format(self.client_address[0], self.client_address[1]))
        while (self.should_run):
            # todo: clarify whether locking (for sending data to the socket) is required in the current threading model
            for ch_id, params in self.session.items():
                try:
                    ch_type = GLOBAL_CONFIG['equipment'][ch_id][0]
                    if ch_type == 'a429rx':
                        for label in params:
                            if label in GLOBAL_CONFIG['sample_data']:
                                time.sleep(GLOBAL_CONFIG['data_generator_word_delay'])

                                data_bytes = '{:x}'.format(GLOBAL_CONFIG['sample_data'][label]).encode('ascii')
                                message = b'data,' + str(STAPHandler.get_ts()).encode('ascii') + b',' + \
                                    str(ch_id).encode('ascii') + b',' + \
                                    '{:o}'.format(label).encode('ascii') + b',' + \
                                    (b'0' if len(data_bytes) % 2 == 1 else b'') + data_bytes
                                client.sendall(message)
                                if self.crc32:
                                    client.sendall(STAPHandler.get_crc_bytes(message))
                                client.sendall(b'\r\n')

                    elif ch_type == 'a717rx':
                        for subframe in range(len(params)):
                            for word in params[subframe]:
                                time.sleep(GLOBAL_CONFIG['data_generator_word_delay'])
                                message = b'data,' + str(STAPHandler.get_ts()).encode('ascii') + b',' + \
                                    str(ch_id).encode('ascii') + b',' + \
                                    str(subframe).encode('ascii') + b',' + \
                                    str(word).encode('ascii') + b',' + \
                                    b'0fff'
                                client.sendall(message)
                                if self.crc32:
                                    client.sendall(STAPHandler.get_crc_bytes(message))
                                client.sendall(b'\r\n')

                    elif ch_type == 'disc':
                        time.sleep(GLOBAL_CONFIG['data_generator_word_delay'])
                        message = b'data,' + str(STAPHandler.get_ts()).encode('ascii') + b',' + \
                            b'disc,' + \
                            str(ch_id).encode('ascii') + b',' + \
                            b'1'
                        client.sendall(message)
                        if self.crc32:
                            client.sendall(STAPHandler.get_crc_bytes(message))
                        client.sendall(b'\r\n')
                except:
                    Logger.info('Error sending data to the client {}:{}. Interrupting the data delivery thread.'.format(self.client_address[0], self.client_address[1]))
                    return
            time.sleep(GLOBAL_CONFIG['data_generator_interval'])
        Logger.info('Data generator for the client {}:{} quits.'.format(self.client_address[0], self.client_address[1]))

    def handle_request(self, request):
        args = request.split(b',')
        if args[0] == b'status':
            if len(args) != 1:
                return STAPHandler.get_err('INV_ARG_NO')
                
            equipment = b''
            for ch_id, channel in GLOBAL_CONFIG['equipment'].items():
                if len(equipment) > 0:
                    equipment += b','
                equipment += channel[0].encode('ascii') + b'{' + str(ch_id).encode('ascii')
                for prop in channel[1:]:
                    equipment += b',' + str(prop).encode('ascii')
                equipment += b'}'
            equipment = b'equipment{' + equipment + b'}'
            
            session = b''
            for ch_id, params in self.session.items():
                ch_type = GLOBAL_CONFIG['equipment'][ch_id][0]
                if ch_type == 'a429rx':
                    for label in params:
                        if len(session) > 0:
                            session += b','
                        session += b'a429{' + str(ch_id).encode('ascii') + b',' + '{:o}'.format(label).encode('ascii') + b'}'
                elif ch_type == 'a717rx':
                    for subframe in range(len(params)):
                        for word in params[subframe]:
                            if len(session) > 0:
                                session += b','
                            session += b'a717{' + str(ch_id).encode('ascii') + b',' + str(subframe).encode('ascii') + b',' + str(word).encode('ascii') + b'}'
                elif ch_type == 'disc':
                    if len(session) > 0:
                            session += b','
                    session += b'disc{' + str(ch_id).encode('ascii') + b',' + str(params).encode('ascii') + b'}'
            session = b'session{' + session + b'}'
            
            return b'status,' + \
                GLOBAL_CONFIG['stap_version'].encode('ascii') + b',' + \
                equipment + b',' + \
                session
                
        elif args[0] == b'add':
            if len(args) != 3 and len(args) != 4:
                return STAPHandler.get_err('INV_ARG_NO')
            
            if args[1] == b'disc':
                try:
                    ch_id = int(args[2])
                except:
                    return STAPHandler.get_err('INV_CHANNEL_FORMAT')
                
                if ch_id in GLOBAL_CONFIG['equipment']:
                    channel = GLOBAL_CONFIG['equipment'][ch_id]
                    if channel[0] == 'disc':
                        if channel[1] == 'in':
                            try:
                                frequency = int(args[3])
                            except:
                                return STAPHandler.get_err('INV_FREQ_FORMAT')
                            
                            if frequency >= 5:
                                if ch_id in self.session:
                                    return STAPHandler.get_err('DISC_ALREADY_SUBS')
                                else:
                                    self.session[ch_id] = frequency
                                    return b'ok'
                            else:
                                return STAPHandler.get_err('INV_FREQUENCY_RANGE')
                        else:
                            return STAPHandler.get_err('INV_CHANNEL_TYPE_DISC_IN')
                    else:
                        return STAPHandler.get_err('INV_CHANNEL_TYPE_DISC')
                return STAPHandler.get_err('CHANNEL_NOT_FOUND')
            
            elif args[1] == b'generic':
                return STAPHandler.get_err('GENERIC_UNSUPPORTED')

            else:
                try:
                    ch_id = int(args[1])
                except:
                    return STAPHandler.get_err('INV_CHANNEL_FORMAT')
                        
                if ch_id in GLOBAL_CONFIG['equipment']:
                    channel = GLOBAL_CONFIG['equipment'][ch_id]

                    if channel[0] == 'a429rx':
                        try:
                            label = args[2] if args[2] == b'all' else int(args[2], 8)
                        except:
                            return STAPHandler.get_err('INV_LABEL_FORMAT')
                        
                        if label != b'all' and (label < 0 or label > 255):
                            return STAPHandler.get_err('INV_LABEL_RANGE')
                        
                        if label == b'all':
                            self.session[ch_id] = set(range(256))
                        else:
                            if ch_id in self.session:
                                if label in self.session[ch_id]:
                                    return STAPHandler.get_err('LABEL_ALREADY_SUBS')
                                else:
                                    self.session[ch_id].add(label)
                            else:
                                self.session[ch_id] = { label }
                        
                        return b'ok'
                        
                    elif channel[0] == 'a717rx':
                        try:
                            subframe = args[2] if args[2] == b'all' else int(args[2])
                        except:
                            return STAPHandler.get_err('INV_SUBFRAME_FORMAT')
                        
                        try:
                            word = args[3] if args[3] == b'all' else int(args[3])
                        except:
                            return STAPHandler.get_err('INV_WORD_FORMAT')
                        
                        if subframe != b'all' and (subframe < 0 or subframe >= 4):
                            return STAPHandler.get_err('INV_SUFRAME_RANGE')
                            
                        if word != b'all' and (word < 0 or word >= channel[1]):
                            return STAPHandler.get_err('INV_WORD_RANGE')
                            
                        if ch_id not in self.session:
                            self.session[ch_id] = [set() for x in range(4)]
                        
                        if subframe == b'all':
                            # in case of 'all' approach, no existing subscription will be checked
                            if word == b'all':
                                for subframe in range(4):
                                    self.session[ch_id][subframe].update(set(range(channel[1])))
                            else:
                                for subframe in range(4):
                                    self.session[ch_id][subframe].add(word)
                        else:
                            if word == b'all':
                                # in case of 'all' approach, no existing subscription will be checked
                                self.session[ch_id][subframe].update(set(range(channel[1])))
                            else:
                                if word in self.session[ch_id][subframe]:
                                    return STAPHandler.get_err('WORD_ALREADY_SUBS')
                                else:
                                    self.session[ch_id][subframe].add(word)
                        return b'ok'
            
                return STAPHandler.get_err('CHANNEL_NOT_FOUND')

        elif args[0] == b'remove':
            if len(args) != 3 and len(args) != 4:
                return STAPHandler.get_err('INV_ARG_NO')
                
            if args[1] == b'disc':
                try:
                    ch_id = int(args[2])
                except:
                    return STAPHandler.get_err('INV_CHANNEL_FORMAT')
                    
                if ch_id in GLOBAL_CONFIG['equipment']:
                    channel = GLOBAL_CONFIG['equipment'][ch_id]
                    
                    if channel[0] == 'disc':
                        if channel[1] == 'in':
                            if ch_id in self.session:
                                del self.session[ch_id]
                                return b'ok'
                            else:
                                return STAPHandler.get_err('DISC_NOT_SUBS')
                        else:
                            return STAPHandler.get_err('INV_CHANNEL_TYPE_DISC_IN')
                    else:
                        return STAPHandler.get_err('INV_CHANNEL_TYPE_DISC')
                        
                return STAPHandler.get_err('CHANNEL_NOT_FOUND')
            
            elif args[1] == b'generic':
                return STAPHandler.get_err('GENERIC_UNSUPPORTED')

            else:
                try:
                    ch_id = int(args[1])
                except:
                    return STAPHandler.get_err('INV_CHANNEL_FORMAT')

                if ch_id in GLOBAL_CONFIG['equipment']:
                    channel = GLOBAL_CONFIG['equipment'][ch_id]
                    
                    if channel[0] == 'a429rx':
                        try:
                            label = args[2] if args[2] == b'all' else int(args[2], 8)
                        except:
                            return STAPHandler.get_err('INV_LABEL_FORMAT')
                        
                        if label != b'all' and (label < 0 or label > 255):
                            return STAPHandler.get_err('INV_LABEL_RANGE')
                        
                        if label == b'all':
                            self.session[ch_id] = set()
                        else:
                            if ch_id in self.session:
                                try:
                                    self.session[ch_id].remove(label)
                                except:
                                    return STAPHandler.get_err('LABEL_NOT_SUBS')
                            else:
                                return STAPHandler.get_err('LABEL_NOT_SUBS')
                        
                        return b'ok'
                        
                    elif channel[0] == 'a717rx':
                        try:
                            subframe = args[2] if args[2] == b'all' else int(args[2])
                        except:
                            return STAPHandler.get_err('INV_SUBFRAME_FORMAT')
                        
                        try:
                            word = args[3] if args[3] == b'all' else int(args[3])
                        except:
                            return STAPHandler.get_err('INV_WORD_FORMAT')
                        
                        if subframe != b'all' and (subframe < 0 or subframe >= 4):
                            return STAPHandler.get_err('INV_SUFRAME_RANGE')
                            
                        if word != b'all' and (word < 0 or word >= channel[1]):
                            return STAPHandler.get_err('INV_WORD_RANGE')

                        if subframe == b'all':
                            # in case of 'all' approach, no existing subscription will be checked
                            if ch_id in self.session:
                                if word == b'all':
                                    del self.session[ch_id]
                                else:
                                    for subframe in range(4):
                                        self.session[ch_id][subframe].discard(word)
                        else:
                            if word == b'all':
                                # in case of 'all' approach, no existing subscription will be checked
                                if ch_id in self.session:
                                    self.session[ch_id][subframe] = set()
                            else:
                                try:
                                    self.session[ch_id][subframe].remove(word)
                                except:
                                    return STAPHandler.get_err('WORD_NOT_SUBS')

                        return b'ok'
            
                return STAPHandler.get_err('CHANNEL_NOT_FOUND')
            
        elif args[0] == b'lock' or args[0] == b'release':
            
            if len(args) == 2:
                try:
                    ch_id = int(args[1])
                except:
                    return STAPHandler.get_err('INV_CHANNEL_FORMAT')
                    
                if ch_id in GLOBAL_CONFIG['equipment']:
                    channel = GLOBAL_CONFIG['equipment'][ch_id]

                    if channel[0] == 'a429tx' or channel[0] == 'disc' and channel[1] == 'out':
                        return b'ok'
                    else:
                        return STAPHandler.get_err('INV_CHANNEL_TYPE_OUTPUT')
                
                return STAPHandler.get_err('CHANNEL_NOT_FOUND')
            else:
                return STAPHandler.get_err('INV_ARG_NO')
                    
        elif args[0] == b'transmit':
            if len(args) != 4:
                return STAPHandler.get_err('INV_ARG_NO')
            
            try:
                ch_id = int(args[1])
            except:
                return STAPHandler.get_err('INV_CHANNEL_FORMAT')
                
            if ch_id in GLOBAL_CONFIG['equipment']:
                if GLOBAL_CONFIG['equipment'][ch_id][0] != 'a429tx':
                    return STAPHandler.get_err('INV_CHANNEL_TYPE_A429TX')
            else:
                return STAPHandler.get_err('CHANNEL_NOT_FOUND')
                
            try:
                label = int(args[2], 8)
            except:
                return STAPHandler.get_err('INV_LABEL_FORMAT')
                
            if label < 0 or label > 255:
                return STAPHandler.get_err('INV_LABEL_RANGE')
                
            try:
                data = int(args[3], 16)
            except:
                return STAPHandler.get_err('INV_DATA_FORMAT')
            
            if data < 0 or data > 0x7fffff:
                return STAPHandler.get_err('INV_DATA_RANGE')
                
            return b'ok'            

        elif args[0] == b'put':
            if len(args) != 3:
                return STAPHandler.get_err('INV_ARG_NO')
            try:
                ch_id = int(args[1])
            except:
                return STAPHandler.get_err('INV_CHANNEL_FORMAT')
                    
            if ch_id in GLOBAL_CONFIG['equipment']:
                channel = GLOBAL_CONFIG['equipment'][ch_id]
                
                if channel[0] == 'disc':
                    if channel[1] == 'out':
                        if args[2] == b'0' or args[2] == b'1':
                            return b'ok'
                        else:
                            return STAPHandler.get_err('INV_STATE_VALUE')
                    else:
                        return STAPHandler.get_err('INV_CHANNEL_TYPE_DISC_OUT')
                else:
                    return STAPHandler.get_err('INV_CHANNEL_TYPE_DISC')
            
            return STAPHandler.get_err('CHANNEL_NOT_FOUND')

        elif args[0] == b'get':
            if len(args) != 2:
                return STAPHandler.get_err('INV_ARG_NO')
                
            try:
                ch_id = int(args[1])
            except:
                return STAPHandler.get_err('INV_CHANNEL_FORMAT')
                    
            if ch_id in GLOBAL_CONFIG['equipment']:
                channel = GLOBAL_CONFIG['equipment'][ch_id]
                if channel[0] == 'disc':
                    if channel[1] == 'in':
                        return b'data,' + str(STAPHandler.get_ts()).encode('ascii') + b',' + args[1] + b',1'
                    else:
                        return STAPHandler.get_err('INV_CHANNEL_TYPE_DISC_IN')
                else:
                    return STAPHandler.get_err('INV_CHANNEL_TYPE_DISC')
            
            return STAPHandler.get_err('CHANNEL_NOT_FOUND')

        elif args[0] == b'transmitex':
            if len(args) < 3:
                return STAPHandler.get_err('INV_ARG_NO')
                
            try:
                ch_id = int(args[1])
            except:
                return STAPHandler.get_err('INV_CHANNEL_FORMAT')
                
            if ch_id in GLOBAL_CONFIG['equipment']:
                if GLOBAL_CONFIG['equipment'][ch_id][0] != 'a429tx':
                    return STAPHandler.get_err('INV_CHANNEL_TYPE_A429TX')
            else:
                return STAPHandler.get_err('CHANNEL_NOT_FOUND')
                
            try:
                total_words = int(args[2])
            except:
                return STAPHandler.get_err('INV_WORDCOUNT_FORMAT')
            
            if total_words > GLOBAL_CONFIG['max_transmitex_words']:
                return STAPHandler.get_err('INV_WORDCOUNT_RANGE')
            
            if len(args) != (total_words * 2) + 3:
                return STAPHandler.get_err('INV_ARG_NO')
                
            for i in range(total_words):
                try:
                    label = int(args[3 + i * 2], 8)
                except:
                    return STAPHandler.get_err('INV_LABEL_FORMAT')
                    
                if label < 0 or label > 255:
                    return STAPHandler.get_err('INV_LABEL_RANGE')
                    
                try:
                    data = int(args[4 + i * 2], 16)
                except:
                    return STAPHandler.get_err('INV_DATA_FORMAT')
                
                if data < 0 or data > 0x7fffff:
                    return STAPHandler.get_err('INV_DATA_RANGE')
                
            return b'ok'            

        elif request == b'checksum,crc32,on':
            self.crc32 = True
            return b'ok'
            
        elif request == b'checksum,off':
            self.crc32 = False
            return b'ok'
        
        elif args[0] == b'checksum':
            if len(args) < 2:
                return STAPHandler.get_err('INV_ARG_NO')

            if args[1] != b'crc32' and args[1] != b'off':
                return STAPHandler.get_err('INV_CHECKSUM_MODE')
                
            if args[1] == b'crc32':
                if len(args) != 3:
                    return STAPHandler.get_err('INV_ARG_NO')
                elif args[2] != b'on':
                    return STAPHandler.get_err('INV_CRC32_MODE')
            elif args[1] == b'off':
                if len(args) != 2:
                    return STAPHandler.get_err('INV_ARG_NO')
            
            return STAPHandler.get_err('UNKNOWN_ERROR')
            
        else:        
            return STAPHandler.get_err('UNKNOWN_COMMAND')
        
    def handle(self):
        Logger.info("Incoming connection from {}:{}.".format(self.client_address[0], self.client_address[1]))

        self.crc32 = False
        self.session = dict()
        self.buffer = b''
        
        self.should_run = True
        data_thread = threading.Thread(target = self.data_generator, args = (self.request,))
        data_thread.daemon = True
        data_thread.start()
        
        while True:
            try:
                received = self.request.recv(1024) # may throw exception
            except:
                Logger.info('Error reading from the client {}:{}. Closing connection.'.format(self.client_address[0], self.client_address[1]))
                self.should_run = False
                return

            Logger.debug('Data received {}.'.format(received))
            
            if len(received) == 0:
                Logger.info('Connection from the client {}:{} closed.'.format(self.client_address[0], self.client_address[1]))
                self.should_run = False
                return
            
            self.buffer += received
            
            # protection against too long requests
            if len(self.buffer) > GLOBAL_CONFIG['max_input_buffer']:
                # silent cut
                Logger.info('Max buffer size reached ({}), forgetting current data.'.format(GLOBAL_CONFIG['max_input_buffer']))
                self.buffer = b''
            
            # iterate over the buffer to find all commands
            while True:
                # find the first line break if any -> pos_nl
                pos_r = self.buffer.find(b'\r')
                pos_n = self.buffer.find(b'\n')
                if pos_r >= 0 and pos_n >=0:
                    pos_nl = pos_r if pos_r < pos_n else pos_n
                else:
                    pos_nl = pos_r if pos_r >= 0 else pos_n
                    
                # interpret as a command if there is a new-line sequence only
                if pos_nl >= 0:
                    request = self.buffer[0:pos_nl]
                    
                    pos = 0
                    while pos < len(request):
                        if request[pos] == 0x08:
                            request = request[:(pos - 1) if pos > 0 else pos] + request[pos+1:]
                            pos -= 1 if pos > 0 else 0
                        else:
                            pos += 1
                    
                    self.buffer = self.buffer[pos_nl+1:]

                    # process the command if not empty only
                    if len(request) > 0:
                        # verify, whether a checksum is expected and validate it
                        response = None
                        if self.crc32:
                            rpos = request.rfind(b',')
                            if rpos < 0:
                                response = STAPHandler.get_err('CHECKSUM_MISSING')
                            else:
                                try:
                                    checksum_given = int(request[rpos+1:], 16)
                                    checksum_calculated = zlib.crc32(request[0:rpos+1])
                                    if checksum_given == checksum_calculated:
                                        request = request[0:rpos]
                                    else:
                                        response = STAPHandler.get_err('INV_CHECKSUM_VALUE')
                                except:
                                    response = STAPHandler.get_err('INV_CHECKSUM_FORMAT')
                        
                        # an existing respone means that there was a problem with the request at the previous stage already
                        # (checksum validation)
                        # in this case, no further processing will be done
                        if response == None:
                            response = self.handle_request(request)

                        try:
                            self.request.sendall(response)
                            if self.crc32:
                                self.request.sendall(STAPHandler.get_crc_bytes(response))
                            self.request.sendall(b'\r\n')
                        except:
                            Logger.info('Error writing to the client {}:{}. Closing connection.'.format(self.client_address[0], self.client_address[1]))
                            self.should_run = False
                            return
                else:
                    # no more commands in the buffer
                    break

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, hostandport, handler):
        super().__init__(hostandport, handler)
        self.daemon_threads = True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as config_file:
            try:
                config_data = json.load(config_file)
                if 'equipment' in config_data:
                    equipment = {}
                    for id, value in config_data['equipment'].items():
                        equipment[int(id)] = value
                    config_data['equipment'] = equipment
                    
                if 'sample_data' in config_data:
                    sample_data = {}
                    for id, value in config_data['sample_data'].items():
                        sample_data[int(id)] = value
                    config_data['sample_data'] = sample_data

                GLOBAL_CONFIG.update(config_data)
            except Exception as ex:
                Logger.error('Failed to load the config file {} due to {}. Falling back to defaults.'.format(sys.argv[1], str(ex)))
                
    print(json.dumps(GLOBAL_CONFIG, indent=4))

    Logger.info('Staring STAP server on {}:{}...'.format(GLOBAL_CONFIG['host'], GLOBAL_CONFIG['port']))

    server = ThreadedTCPServer((GLOBAL_CONFIG['host'], GLOBAL_CONFIG['port']), STAPHandler)

    with server:
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        text = input('Press enter to exit the main loop...')
        server.shutdown()
        Logger.info('Server shutdown has been called.')

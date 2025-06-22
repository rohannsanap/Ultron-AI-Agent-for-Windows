import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { TypeAnimation } from 'react-type-animation';
import { 
  Mic, Send, Settings, Command, Zap, FileText, 
  Monitor, Shield, Leaf, MicOff, FolderOpen, Info 
} from 'lucide-react';

// Define Timer type to avoid NodeJS namespace requirement
type Timer = ReturnType<typeof setTimeout>;

interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly [index: number]: SpeechRecognitionAlternative;
  length: number;
}

interface SpeechRecognitionAlternative {
  readonly transcript: string;
  readonly confidence: number;
}

interface SpeechRecognitionResultList {
  readonly length: number;
  readonly [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionEvent {
  readonly results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent {
  readonly error: string;
  readonly message: string;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: (event: SpeechRecognitionEvent) => void;
  onerror: (event: SpeechRecognitionErrorEvent) => void;
}

interface Response {
  text: string;
  isUser: boolean;
}

interface HelpInfo {
  basic_commands: string[];
  advanced_commands: string[];
}

function App() {
  const [message, setMessage] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [responses, setResponses] = useState<Response[]>([
    { text: "How can I help you today? Try asking me to create, move, or delete files and folders.", isUser: false }
  ]);
  const [helpInfo, setHelpInfo] = useState<HelpInfo | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  
  // Use Timer type instead of NodeJS.Timeout
  const autoSubmitTimerRef = useRef<Timer | null>(null);
  const lastActivityRef = useRef<number>(Date.now());
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  
  // Fetch help information when component mounts
  useEffect(() => {
    fetch('http://localhost:5000/api/get-help')
      .then(response => response.json())
      .then(data => setHelpInfo(data))
      .catch(error => console.error('Error fetching help info:', error));
  }, []);
  
  useEffect(() => {
    const SpeechRecognitionConstructor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognitionConstructor) {
      const recognition = new SpeechRecognitionConstructor() as SpeechRecognition;
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const results = event.results;
        const lastResultIndex = results.length - 1;
        // Corrected access to transcript
        const transcript = results[lastResultIndex][0].transcript;
        
        setMessage(transcript);
        lastActivityRef.current = Date.now(); 
        
        if (autoSubmitTimerRef.current) {
          clearTimeout(autoSubmitTimerRef.current);
        }
        
        autoSubmitTimerRef.current = setTimeout(() => {
          if (transcript.trim() && isListening) {
            handleSendMessage();
          }
        }, 4000);
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) recognitionRef.current.stop();
      if (autoSubmitTimerRef.current) clearTimeout(autoSubmitTimerRef.current);
    };
  }, []);

  const synth = window.speechSynthesis;

  const toggleListening = () => {
    if (!recognitionRef.current) return;
    
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const startListening = () => {
    if (!recognitionRef.current || isProcessing) return;
    
    recognitionRef.current.start();
    setIsListening(true);
  
    if (autoSubmitTimerRef.current) {
      clearTimeout(autoSubmitTimerRef.current);
    }
    
    autoSubmitTimerRef.current = setTimeout(() => {
      if (message.trim() && isListening) {
        handleSendMessage();
      }
    }, 5000);
  };

  const stopListening = () => {
    if (!recognitionRef.current) return;
    
    recognitionRef.current.stop();
    setIsListening(false);
    
    if (autoSubmitTimerRef.current) {
      clearTimeout(autoSubmitTimerRef.current);
      autoSubmitTimerRef.current = null;
    }
  };

  const speak = (text: string) => {
    const utterance = new SpeechSynthesisUtterance(text);
    
    utterance.onstart = () => {
      if (isListening) {
        stopListening();
      }
    };
    
    utterance.onend = () => {
      setIsProcessing(false);
    };
    
    synth.speak(utterance);
  };

  const handleSendMessage = async () => {
    if (!message.trim()) return;
    
    stopListening();
    setIsProcessing(true);
    setResponses(prev => [...prev, { text: message, isUser: true }]);

    try {
      const response = await fetch('http://localhost:5000/api/process-command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ command: message }),
      });
      
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      
      const data = await response.json();
      const aiResponse = data.response || "I couldn't process that command. Please try again.";
      
      setResponses(prev => [...prev, { text: aiResponse, isUser: false }]);
      speak(aiResponse);
    } catch (error) {
      console.error('Error processing command:', error);
      const errorResponse = "Sorry, there was an error processing your command. Please try again.";
      setResponses(prev => [...prev, { text: errorResponse, isUser: false }]);
      speak(errorResponse);
      setIsProcessing(false);
    }

    setMessage('');
  };
  
  useEffect(() => {
    if (message.trim()) {
      lastActivityRef.current = Date.now();
      
      if (autoSubmitTimerRef.current) {
        clearTimeout(autoSubmitTimerRef.current);
      }
      
      autoSubmitTimerRef.current = setTimeout(() => {
        if (message.trim() && isListening) {
          handleSendMessage();
        }
      }, 4000); 
    }
    
    return () => {
      if (autoSubmitTimerRef.current) {
        clearTimeout(autoSubmitTimerRef.current);
      }
    };
  }, [message]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [responses]);

  const toggleHelp = () => {
    setShowHelp(!showHelp);
  };

  const features = [
    { icon: Command, title: 'Voice Commands', description: 'Control your files with simple voice instructions' },
    { icon: Monitor, title: 'Cross-Platform', description: 'Works seamlessly across Windows, macOS, and Linux' },
    { icon: Shield, title: 'Secure Operations', description: 'Safe and controlled file system management' },
    { icon: Leaf, title: 'AI-Powered', description: 'Intelligent processing of natural language commands' }
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="container mx-auto px-4 py-12"
      >
        <nav className="flex justify-between items-center mb-16">
          <motion.div 
            initial={{ x: -20 }}
            animate={{ x: 0 }}
            className="flex items-center gap-2"
          >
            <FolderOpen className="w-8 h-8 text-blue-500" />
            <span className="text-xl font-bold">Voice File Manager</span>
          </motion.div>
          <div className="flex items-center gap-2">
            <motion.button
              whileHover={{ scale: 1.05 }}
              className="p-2 rounded-full hover:bg-gray-800"
              onClick={toggleHelp}
            >
              <Info className="w-6 h-6" />
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              className="p-2 rounded-full hover:bg-gray-800"
            >
              <Settings className="w-6 h-6" />
            </motion.button>
          </div>
        </nav>
      
        <div className="max-w-4xl mx-auto">
          <motion.div 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="text-center mb-12"
          >
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              Your Intelligent File
              <span className="text-blue-500"> Assistant</span>
            </h1>
            <TypeAnimation
              sequence={[
                'Create files with your voice...',
                1000,
                'Manage folders effortlessly...',
                1000,
                'Move and rename with simple commands...',
                1000,
              ]}
              wrapper="p"
              speed={50}
              className="text-xl text-gray-400"
              repeat={Infinity}
            />
          </motion.div>
          
          {showHelp && helpInfo && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-800 p-6 rounded-2xl shadow-xl mb-6"
            >
              <h3 className="text-xl font-bold mb-4 text-blue-400">Available Commands</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-lg font-semibold mb-2">Basic Commands:</h4>
                  <ul className="list-disc pl-5 text-gray-300">
                    {helpInfo.basic_commands.map((cmd, idx) => (
                      <li key={idx} className="mb-1">{cmd}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="text-lg font-semibold mb-2">Advanced Commands:</h4>
                  <ul className="list-disc pl-5 text-gray-300">
                    {helpInfo.advanced_commands.map((cmd, idx) => (
                      <li key={idx} className="mb-1">{cmd}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </motion.div>
          )}
          
          <motion.div 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="bg-gray-800 p-6 rounded-2xl shadow-xl mb-12"
          >
            <div className="min-h-[300px] mb-4 bg-gray-900 rounded-xl p-4 overflow-y-auto max-h-[400px]">
              {responses.map((response, index) => (
                <div key={index} className={`flex items-start gap-4 mb-4 ${response.isUser ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full ${response.isUser ? 'bg-blue-600' : 'bg-blue-500'} flex items-center justify-center`}>
                    {response.isUser ? <FileText className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
                  </div>
                  <div className={`${response.isUser ? 'bg-blue-600' : 'bg-gray-800'} rounded-2xl p-4 max-w-[80%]`}>
                    <p>{response.text}</p>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            <div className="flex gap-4">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleListening}
                disabled={isProcessing}
                className={`p-3 rounded-full ${
                  isProcessing ? 'bg-gray-600 cursor-not-allowed' : 
                  isListening ? 'bg-red-500 hover:bg-red-600' : 
                  'bg-blue-500 hover:bg-blue-600'
                }`}
              >
                {isListening ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
              </motion.button>
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Type your file command or press microphone..."
                className="flex-1 bg-gray-900 rounded-xl px-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isProcessing}
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSendMessage}
                disabled={!message.trim() || isProcessing}
                className={`p-3 rounded-full ${
                  !message.trim() || isProcessing ? 
                  'bg-gray-600 cursor-not-allowed' : 
                  'bg-blue-500 hover:bg-blue-600'
                }`}
              >
                <Send className="w-6 h-6" />
              </motion.button>
            </div>
            {isListening && (
              <div className="text-xs text-blue-400 mt-2 flex items-center">
                <Mic className="w-3 h-3 mr-1" />
                <span>Listening... (Auto-submit in 7s of silence)</span>
              </div>
            )}
            {isProcessing && (
              <div className="text-xs text-yellow-400 mt-2 flex items-center">
                <span>Processing your command...</span>
              </div>
            )}
          </motion.div>

          <div className="grid md:grid-cols-2 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.3 + index * 0.1 }}
                className="bg-gray-800 p-6 rounded-xl hover:bg-gray-750 transition-colors"
              >
                <feature.icon className="w-8 h-8 text-blue-500 mb-4" />
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-gray-400">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default App;
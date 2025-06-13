import React, { useState } from 'react';
import './ProphitGpt.css';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane, faPlus, faMicrophone } from '@fortawesome/free-solid-svg-icons';
import logo from '../assets/logo.png'; // main logo
import chatgptLogo from '../assets/logos/icons8-chatgpt-50.png'; // OpenAI/ChatGPT logo for powered-by

// Markdown & syntax highlighting
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

const ProphitGpt: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isAiTyping, setIsAiTyping] = useState(false);

  const handleSendMessage = async (messageTextOverride?: string) => {
    const textToActuallySend = messageTextOverride || inputText;

    if (textToActuallySend.trim() === '') return;

    const newUserMessage: Message = {
      id: `user-${Date.now()}`,
      text: textToActuallySend,
      sender: 'user',
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, newUserMessage]);
    setInputText(''); // Clear input after sending
    setIsAiTyping(true);

    try {
      const backendUrl = (import.meta as any).env?.VITE_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/prophitgpt/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          message: textToActuallySend,
          history: [...messages, newUserMessage].map(({ sender, text }) => ({
            role: sender === 'user' ? 'user' : 'assistant',
            content: text,
          })),
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch response from ProphitGPT');
      }

      const data = await response.json();
      const aiResponse: Message = {
        id: `ai-${Date.now()}`,
        text: data.response,
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      console.error(error);
      const errorResponse: Message = {
        id: `ai-${Date.now()}`,
        text: 'Sorry, I encountered an error processing your request.',
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorResponse]);
    } finally {
      setIsAiTyping(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputText(e.target.value);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(); // Sends content of inputText
    }
  };

  // Suggested prompts based on the screenshots
  const suggestedPrompts = [
    "What are the latest market trends?",
    "Analyze my portfolio's risk.",
    "Suggest some undervalued tech stocks.",
    "Explain the concept of quantitative easing.",
  ];

  return (
    <div className="prophitgpt-container">
      {/* Header */}
      <div className="prophitgpt-header">
        <span className="powered-text">Powered by</span>
        <img src={chatgptLogo} alt="OpenAI logo" className="powered-logo" />
      </div>
      <div className="prophitgpt-chat-area">
        {messages.length === 0 && !isAiTyping && (
          <div className="prophitgpt-welcome">
            <div className="welcome-logo-title-container">
              <img src={logo} alt="ProphitAI Logo" className="welcome-logo" />
            </div>
            <div className="suggested-prompts">
              {suggestedPrompts.map((prompt, index) => (
                <button 
                  key={index} 
                  className="prompt-button"
                  onClick={() => {
                    setInputText(prompt); // Populate input field visually
                    handleSendMessage(prompt); // Immediately send this specific prompt
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map(msg => (
          <div key={msg.id} className={`message-bubble ${msg.sender}`}>
            <div className="message-content">
              {msg.sender === 'ai' ? (
                <ReactMarkdown
                  children={msg.text}
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    code({node, inline, className, children, ...props}: any) {
                      if (inline) {
                        return (
                          <code className="bg-gray-100 px-1 rounded" {...props}>
                            {children}
                          </code>
                        );
                      }
                      return (
                        <pre className="bg-gray-900 text-gray-100 p-3 rounded overflow-auto">
                          <code className={className} {...props}>{children}</code>
                        </pre>
                      );
                    },
                  }}
                />
              ) : (
                msg.text
              )}
            </div>
            <div className="message-timestamp">
              {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        ))}
        {isAiTyping && (
          <div className="message-bubble ai typing-indicator">
            <div className="message-content">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
      </div>
      <div className="prophitgpt-input-area">
        <button className="input-action-button">
          <FontAwesomeIcon icon={faPlus} />
        </button>
        <input
          type="text"
          value={inputText}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          placeholder="Ask ProphitGPT anything..."
          className="prophitgpt-input"
        />
        <button className="input-action-button">
          <FontAwesomeIcon icon={faMicrophone} />
        </button>
        <button 
          className="send-button" 
          onClick={() => handleSendMessage()} // Sends content of inputText
          disabled={inputText.trim() === '' || isAiTyping}
        >
          <FontAwesomeIcon icon={faPaperPlane} />
        </button>
      </div>
    </div>
  );
};

export default ProphitGpt; 
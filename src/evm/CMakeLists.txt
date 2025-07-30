set(EVM_SRCS interpreter.cpp opcode_handlers.cpp evm.cpp)

add_library(evm OBJECT ${EVM_SRCS})

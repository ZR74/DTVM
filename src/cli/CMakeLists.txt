# Copyright (C) 2021-2023 the DTVM authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

add_executable(dtvm dtvm.cpp)
target_link_libraries(dtvm PRIVATE dtvmcore CLI11::CLI11)
target_link_libraries(dtvm PUBLIC evmc::evmc)

if(ZEN_ENABLE_PROFILER)
  target_link_libraries(dtvm PRIVATE profiler)
endif()

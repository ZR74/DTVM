
======= callee/callee.sol:CalleeContract =======
EVM assembly:
    /* "callee/callee.sol":58:405  contract CalleeContract {... */
  mstore(0x40, 0x80)
  callvalue
  dup1
  iszero
  tag_1
  jumpi
  revert(0x00, 0x00)
tag_1:
  pop
  dataSize(sub_0)
  dup1
  dataOffset(sub_0)
  0x00
  codecopy
  0x00
  return
stop

sub_0: assembly {
        /* "callee/callee.sol":58:405  contract CalleeContract {... */
      mstore(0x40, 0x80)
      callvalue
      dup1
      iszero
      tag_1
      jumpi
      revert(0x00, 0x00)
    tag_1:
      pop
      jumpi(tag_2, lt(calldatasize, 0x04))
      shr(0xe0, calldataload(0x00))
      dup1
      0x0c55699c
      eq
      tag_3
      jumpi
      dup1
      0x4018d9aa
      eq
      tag_4
      jumpi
      dup1
      0x40f006be
      eq
      tag_5
      jumpi
      dup1
      0x5197c7aa
      eq
      tag_6
      jumpi
      dup1
      0x771602f7
      eq
      tag_7
      jumpi
    tag_2:
      revert(0x00, 0x00)
        /* "callee/callee.sol":88:104  uint256 public x */
    tag_3:
      tag_8
      tag_9
      jump	// in
    tag_8:
      mload(0x40)
      tag_10
      swap2
      swap1
      tag_11
      jump	// in
    tag_10:
      mload(0x40)
      dup1
      swap2
      sub
      swap1
      return
        /* "callee/callee.sol":111:167  function setX(uint256 _x) public {... */
    tag_4:
      tag_12
      0x04
      dup1
      calldatasize
      sub
      dup2
      add
      swap1
      tag_13
      swap2
      swap1
      tag_14
      jump	// in
    tag_13:
      tag_15
      jump	// in
    tag_12:
      stop
        /* "callee/callee.sol":351:403  function incrementX() public {... */
    tag_5:
      tag_16
      tag_17
      jump	// in
    tag_16:
      stop
        /* "callee/callee.sol":172:243  function getX() public view returns (uint256) {... */
    tag_6:
      tag_18
      tag_19
      jump	// in
    tag_18:
      mload(0x40)
      tag_20
      swap2
      swap1
      tag_11
      jump	// in
    tag_20:
      mload(0x40)
      dup1
      swap2
      sub
      swap1
      return
        /* "callee/callee.sol":249:345  function add(uint256 a, uint256 b) external pure returns (uint256) {... */
    tag_7:
      tag_21
      0x04
      dup1
      calldatasize
      sub
      dup2
      add
      swap1
      tag_22
      swap2
      swap1
      tag_23
      jump	// in
    tag_22:
      tag_24
      jump	// in
    tag_21:
      mload(0x40)
      tag_25
      swap2
      swap1
      tag_11
      jump	// in
    tag_25:
      mload(0x40)
      dup1
      swap2
      sub
      swap1
      return
        /* "callee/callee.sol":88:104  uint256 public x */
    tag_9:
      sload(0x00)
      dup2
      jump	// out
        /* "callee/callee.sol":111:167  function setX(uint256 _x) public {... */
    tag_15:
        /* "callee/callee.sol":158:160  _x */
      dup1
        /* "callee/callee.sol":154:155  x */
      0x00
        /* "callee/callee.sol":154:160  x = _x */
      dup2
      swap1
      sstore
      pop
        /* "callee/callee.sol":111:167  function setX(uint256 _x) public {... */
      pop
      jump	// out
        /* "callee/callee.sol":351:403  function incrementX() public {... */
    tag_17:
        /* "callee/callee.sol":395:396  1 */
      0x01
        /* "callee/callee.sol":390:391  x */
      0x00
      0x00
        /* "callee/callee.sol":390:396  x += 1 */
      dup3
      dup3
      sload
      tag_28
      swap2
      swap1
      tag_29
      jump	// in
    tag_28:
      swap3
      pop
      pop
      dup2
      swap1
      sstore
      pop
        /* "callee/callee.sol":351:403  function incrementX() public {... */
      jump	// out
        /* "callee/callee.sol":172:243  function getX() public view returns (uint256) {... */
    tag_19:
        /* "callee/callee.sol":209:216  uint256 */
      0x00
        /* "callee/callee.sol":235:236  x */
      sload(0x00)
        /* "callee/callee.sol":228:236  return x */
      swap1
      pop
        /* "callee/callee.sol":172:243  function getX() public view returns (uint256) {... */
      swap1
      jump	// out
        /* "callee/callee.sol":249:345  function add(uint256 a, uint256 b) external pure returns (uint256) {... */
    tag_24:
        /* "callee/callee.sol":307:314  uint256 */
      0x00
        /* "callee/callee.sol":337:338  b */
      dup2
        /* "callee/callee.sol":333:334  a */
      dup4
        /* "callee/callee.sol":333:338  a + b */
      tag_32
      swap2
      swap1
      tag_29
      jump	// in
    tag_32:
        /* "callee/callee.sol":326:338  return a + b */
      swap1
      pop
        /* "callee/callee.sol":249:345  function add(uint256 a, uint256 b) external pure returns (uint256) {... */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":7:84   */
    tag_33:
        /* "#utility.yul":44:51   */
      0x00
        /* "#utility.yul":73:78   */
      dup2
        /* "#utility.yul":62:78   */
      swap1
      pop
        /* "#utility.yul":7:84   */
      swap2
      swap1
      pop
      jump	// out
        /* "#utility.yul":90:208   */
    tag_34:
        /* "#utility.yul":177:201   */
      tag_44
        /* "#utility.yul":195:200   */
      dup2
        /* "#utility.yul":177:201   */
      tag_33
      jump	// in
    tag_44:
        /* "#utility.yul":172:175   */
      dup3
        /* "#utility.yul":165:202   */
      mstore
        /* "#utility.yul":90:208   */
      pop
      pop
      jump	// out
        /* "#utility.yul":214:436   */
    tag_11:
        /* "#utility.yul":307:311   */
      0x00
        /* "#utility.yul":345:347   */
      0x20
        /* "#utility.yul":334:343   */
      dup3
        /* "#utility.yul":330:348   */
      add
        /* "#utility.yul":322:348   */
      swap1
      pop
        /* "#utility.yul":358:429   */
      tag_46
        /* "#utility.yul":426:427   */
      0x00
        /* "#utility.yul":415:424   */
      dup4
        /* "#utility.yul":411:428   */
      add
        /* "#utility.yul":402:408   */
      dup5
        /* "#utility.yul":358:429   */
      tag_34
      jump	// in
    tag_46:
        /* "#utility.yul":214:436   */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":523:640   */
    tag_36:
        /* "#utility.yul":632:633   */
      0x00
        /* "#utility.yul":629:630   */
      0x00
        /* "#utility.yul":622:634   */
      revert
        /* "#utility.yul":769:891   */
    tag_38:
        /* "#utility.yul":842:866   */
      tag_51
        /* "#utility.yul":860:865   */
      dup2
        /* "#utility.yul":842:866   */
      tag_33
      jump	// in
    tag_51:
        /* "#utility.yul":835:840   */
      dup2
        /* "#utility.yul":832:867   */
      eq
        /* "#utility.yul":822:885   */
      tag_52
      jumpi
        /* "#utility.yul":881:882   */
      0x00
        /* "#utility.yul":878:879   */
      0x00
        /* "#utility.yul":871:883   */
      revert
        /* "#utility.yul":822:885   */
    tag_52:
        /* "#utility.yul":769:891   */
      pop
      jump	// out
        /* "#utility.yul":897:1036   */
    tag_39:
        /* "#utility.yul":943:948   */
      0x00
        /* "#utility.yul":981:987   */
      dup2
        /* "#utility.yul":968:988   */
      calldataload
        /* "#utility.yul":959:988   */
      swap1
      pop
        /* "#utility.yul":997:1030   */
      tag_54
        /* "#utility.yul":1024:1029   */
      dup2
        /* "#utility.yul":997:1030   */
      tag_38
      jump	// in
    tag_54:
        /* "#utility.yul":897:1036   */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":1042:1371   */
    tag_14:
        /* "#utility.yul":1101:1107   */
      0x00
        /* "#utility.yul":1150:1152   */
      0x20
        /* "#utility.yul":1138:1147   */
      dup3
        /* "#utility.yul":1129:1136   */
      dup5
        /* "#utility.yul":1125:1148   */
      sub
        /* "#utility.yul":1121:1153   */
      slt
        /* "#utility.yul":1118:1237   */
      iszero
      tag_56
      jumpi
        /* "#utility.yul":1156:1235   */
      tag_57
      tag_36
      jump	// in
    tag_57:
        /* "#utility.yul":1118:1237   */
    tag_56:
        /* "#utility.yul":1276:1277   */
      0x00
        /* "#utility.yul":1301:1354   */
      tag_58
        /* "#utility.yul":1346:1353   */
      dup5
        /* "#utility.yul":1337:1343   */
      dup3
        /* "#utility.yul":1326:1335   */
      dup6
        /* "#utility.yul":1322:1344   */
      add
        /* "#utility.yul":1301:1354   */
      tag_39
      jump	// in
    tag_58:
        /* "#utility.yul":1291:1354   */
      swap2
      pop
        /* "#utility.yul":1247:1364   */
      pop
        /* "#utility.yul":1042:1371   */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":1377:1851   */
    tag_23:
        /* "#utility.yul":1445:1451   */
      0x00
        /* "#utility.yul":1453:1459   */
      0x00
        /* "#utility.yul":1502:1504   */
      0x40
        /* "#utility.yul":1490:1499   */
      dup4
        /* "#utility.yul":1481:1488   */
      dup6
        /* "#utility.yul":1477:1500   */
      sub
        /* "#utility.yul":1473:1505   */
      slt
        /* "#utility.yul":1470:1589   */
      iszero
      tag_60
      jumpi
        /* "#utility.yul":1508:1587   */
      tag_61
      tag_36
      jump	// in
    tag_61:
        /* "#utility.yul":1470:1589   */
    tag_60:
        /* "#utility.yul":1628:1629   */
      0x00
        /* "#utility.yul":1653:1706   */
      tag_62
        /* "#utility.yul":1698:1705   */
      dup6
        /* "#utility.yul":1689:1695   */
      dup3
        /* "#utility.yul":1678:1687   */
      dup7
        /* "#utility.yul":1674:1696   */
      add
        /* "#utility.yul":1653:1706   */
      tag_39
      jump	// in
    tag_62:
        /* "#utility.yul":1643:1706   */
      swap3
      pop
        /* "#utility.yul":1599:1716   */
      pop
        /* "#utility.yul":1755:1757   */
      0x20
        /* "#utility.yul":1781:1834   */
      tag_63
        /* "#utility.yul":1826:1833   */
      dup6
        /* "#utility.yul":1817:1823   */
      dup3
        /* "#utility.yul":1806:1815   */
      dup7
        /* "#utility.yul":1802:1824   */
      add
        /* "#utility.yul":1781:1834   */
      tag_39
      jump	// in
    tag_63:
        /* "#utility.yul":1771:1834   */
      swap2
      pop
        /* "#utility.yul":1726:1844   */
      pop
        /* "#utility.yul":1377:1851   */
      swap3
      pop
      swap3
      swap1
      pop
      jump	// out
        /* "#utility.yul":1857:2037   */
    tag_40:
        /* "#utility.yul":1905:1982   */
      0x4e487b7100000000000000000000000000000000000000000000000000000000
        /* "#utility.yul":1902:1903   */
      0x00
        /* "#utility.yul":1895:1983   */
      mstore
        /* "#utility.yul":2002:2006   */
      0x11
        /* "#utility.yul":1999:2000   */
      0x04
        /* "#utility.yul":1992:2007   */
      mstore
        /* "#utility.yul":2026:2030   */
      0x24
        /* "#utility.yul":2023:2024   */
      0x00
        /* "#utility.yul":2016:2031   */
      revert
        /* "#utility.yul":2043:2234   */
    tag_29:
        /* "#utility.yul":2083:2086   */
      0x00
        /* "#utility.yul":2102:2122   */
      tag_66
        /* "#utility.yul":2120:2121   */
      dup3
        /* "#utility.yul":2102:2122   */
      tag_33
      jump	// in
    tag_66:
        /* "#utility.yul":2097:2122   */
      swap2
      pop
        /* "#utility.yul":2136:2156   */
      tag_67
        /* "#utility.yul":2154:2155   */
      dup4
        /* "#utility.yul":2136:2156   */
      tag_33
      jump	// in
    tag_67:
        /* "#utility.yul":2131:2156   */
      swap3
      pop
        /* "#utility.yul":2179:2180   */
      dup3
        /* "#utility.yul":2176:2177   */
      dup3
        /* "#utility.yul":2172:2181   */
      add
        /* "#utility.yul":2165:2181   */
      swap1
      pop
        /* "#utility.yul":2200:2203   */
      dup1
        /* "#utility.yul":2197:2198   */
      dup3
        /* "#utility.yul":2194:2204   */
      gt
        /* "#utility.yul":2191:2227   */
      iszero
      tag_68
      jumpi
        /* "#utility.yul":2207:2225   */
      tag_69
      tag_40
      jump	// in
    tag_69:
        /* "#utility.yul":2191:2227   */
    tag_68:
        /* "#utility.yul":2043:2234   */
      swap3
      swap2
      pop
      pop
      jump	// out

    auxdata: 0xa2646970667358221220de2729fc5845dc413f4beb1ccc5adf3f4329e4fbede068d8b0b5acf93894174d64736f6c634300081e0033
}


======= caller/caller.sol:CallerContract =======
EVM assembly:
    /* "caller/caller.sol":157:998  contract CallerContract {... */
  mstore(0x40, 0x80)
    /* "caller/caller.sol":314:463  constructor(address calleeAddress) {... */
  callvalue
  dup1
  iszero
  tag_1
  jumpi
  revert(0x00, 0x00)
tag_1:
  pop
  mload(0x40)
  sub(codesize, bytecodeSize)
  dup1
  bytecodeSize
  dup4
  codecopy
  dup2
  dup2
  add
  0x40
  mstore
  dup2
  add
  swap1
  tag_2
  swap2
  swap1
  tag_3
  jump	// in
tag_2:
    /* "caller/caller.sol":442:455  calleeAddress */
  dup1
    /* "caller/caller.sol":418:424  callee */
  0x00
  0x00
    /* "caller/caller.sol":418:456  callee = CalleeContract(calleeAddress) */
  0x0100
  exp
  dup2
  sload
  dup2
  0xffffffffffffffffffffffffffffffffffffffff
  mul
  not
  and
  swap1
  dup4
  0xffffffffffffffffffffffffffffffffffffffff
  and
  mul
  or
  swap1
  sstore
  pop
    /* "caller/caller.sol":314:463  constructor(address calleeAddress) {... */
  pop
    /* "caller/caller.sol":157:998  contract CallerContract {... */
  jump(tag_6)
    /* "#utility.yul":88:205   */
tag_8:
    /* "#utility.yul":197:198   */
  0x00
    /* "#utility.yul":194:195   */
  0x00
    /* "#utility.yul":187:199   */
  revert
    /* "#utility.yul":334:460   */
tag_10:
    /* "#utility.yul":371:378   */
  0x00
    /* "#utility.yul":411:453   */
  0xffffffffffffffffffffffffffffffffffffffff
    /* "#utility.yul":404:409   */
  dup3
    /* "#utility.yul":400:454   */
  and
    /* "#utility.yul":389:454   */
  swap1
  pop
    /* "#utility.yul":334:460   */
  swap2
  swap1
  pop
  jump	// out
    /* "#utility.yul":466:562   */
tag_11:
    /* "#utility.yul":503:510   */
  0x00
    /* "#utility.yul":532:556   */
  tag_20
    /* "#utility.yul":550:555   */
  dup3
    /* "#utility.yul":532:556   */
  tag_10
  jump	// in
tag_20:
    /* "#utility.yul":521:556   */
  swap1
  pop
    /* "#utility.yul":466:562   */
  swap2
  swap1
  pop
  jump	// out
    /* "#utility.yul":568:690   */
tag_12:
    /* "#utility.yul":641:665   */
  tag_22
    /* "#utility.yul":659:664   */
  dup2
    /* "#utility.yul":641:665   */
  tag_11
  jump	// in
tag_22:
    /* "#utility.yul":634:639   */
  dup2
    /* "#utility.yul":631:666   */
  eq
    /* "#utility.yul":621:684   */
  tag_23
  jumpi
    /* "#utility.yul":680:681   */
  0x00
    /* "#utility.yul":677:678   */
  0x00
    /* "#utility.yul":670:682   */
  revert
    /* "#utility.yul":621:684   */
tag_23:
    /* "#utility.yul":568:690   */
  pop
  jump	// out
    /* "#utility.yul":696:839   */
tag_13:
    /* "#utility.yul":753:758   */
  0x00
    /* "#utility.yul":784:790   */
  dup2
    /* "#utility.yul":778:791   */
  mload
    /* "#utility.yul":769:791   */
  swap1
  pop
    /* "#utility.yul":800:833   */
  tag_25
    /* "#utility.yul":827:832   */
  dup2
    /* "#utility.yul":800:833   */
  tag_12
  jump	// in
tag_25:
    /* "#utility.yul":696:839   */
  swap3
  swap2
  pop
  pop
  jump	// out
    /* "#utility.yul":845:1196   */
tag_3:
    /* "#utility.yul":915:921   */
  0x00
    /* "#utility.yul":964:966   */
  0x20
    /* "#utility.yul":952:961   */
  dup3
    /* "#utility.yul":943:950   */
  dup5
    /* "#utility.yul":939:962   */
  sub
    /* "#utility.yul":935:967   */
  slt
    /* "#utility.yul":932:1051   */
  iszero
  tag_27
  jumpi
    /* "#utility.yul":970:1049   */
  tag_28
  tag_8
  jump	// in
tag_28:
    /* "#utility.yul":932:1051   */
tag_27:
    /* "#utility.yul":1090:1091   */
  0x00
    /* "#utility.yul":1115:1179   */
  tag_29
    /* "#utility.yul":1171:1178   */
  dup5
    /* "#utility.yul":1162:1168   */
  dup3
    /* "#utility.yul":1151:1160   */
  dup6
    /* "#utility.yul":1147:1169   */
  add
    /* "#utility.yul":1115:1179   */
  tag_13
  jump	// in
tag_29:
    /* "#utility.yul":1105:1179   */
  swap2
  pop
    /* "#utility.yul":1061:1189   */
  pop
    /* "#utility.yul":845:1196   */
  swap3
  swap2
  pop
  pop
  jump	// out
    /* "caller/caller.sol":157:998  contract CallerContract {... */
tag_6:
  dataSize(sub_0)
  dup1
  dataOffset(sub_0)
  0x00
  codecopy
  0x00
  return
stop

sub_0: assembly {
        /* "caller/caller.sol":157:998  contract CallerContract {... */
      mstore(0x40, 0x80)
      callvalue
      dup1
      iszero
      tag_1
      jumpi
      revert(0x00, 0x00)
    tag_1:
      pop
      jumpi(tag_2, lt(calldatasize, 0x04))
      shr(0xe0, calldataload(0x00))
      dup1
      0x5a361756
      eq
      tag_3
      jumpi
      dup1
      0x5f6cce24
      eq
      tag_4
      jumpi
      dup1
      0x9f8be819
      eq
      tag_5
      jumpi
      dup1
      0xceee2e20
      eq
      tag_6
      jumpi
      dup1
      0xcffb5d72
      eq
      tag_7
      jumpi
    tag_2:
      revert(0x00, 0x00)
        /* "caller/caller.sol":905:996  function getCalleeX() external view returns (uint256) {... */
    tag_3:
      tag_8
      tag_9
      jump	// in
    tag_8:
      mload(0x40)
      tag_10
      swap2
      swap1
      tag_11
      jump	// in
    tag_10:
      mload(0x40)
      dup1
      swap2
      sub
      swap1
      return
        /* "caller/caller.sol":510:583  function setCalleeX(uint256 _x) external {... */
    tag_4:
      tag_12
      0x04
      dup1
      calldatasize
      sub
      dup2
      add
      swap1
      tag_13
      swap2
      swap1
      tag_14
      jump	// in
    tag_13:
      tag_15
      jump	// in
    tag_12:
      stop
        /* "caller/caller.sol":629:740  function callAdd(uint256 a, uint256 b) external view returns (uint256) {... */
    tag_5:
      tag_16
      0x04
      dup1
      calldatasize
      sub
      dup2
      add
      swap1
      tag_17
      swap2
      swap1
      tag_18
      jump	// in
    tag_17:
      tag_19
      jump	// in
    tag_16:
      mload(0x40)
      tag_20
      swap2
      swap1
      tag_11
      jump	// in
    tag_20:
      mload(0x40)
      dup1
      swap2
      sub
      swap1
      return
        /* "caller/caller.sol":225:253  CalleeContract public callee */
    tag_6:
      tag_21
      tag_22
      jump	// in
    tag_21:
      mload(0x40)
      tag_23
      swap2
      swap1
      tag_24
      jump	// in
    tag_23:
      mload(0x40)
      dup1
      swap2
      sub
      swap1
      return
        /* "caller/caller.sol":793:864  function callIncrementX() external {... */
    tag_7:
      tag_25
      tag_26
      jump	// in
    tag_25:
      stop
        /* "caller/caller.sol":905:996  function getCalleeX() external view returns (uint256) {... */
    tag_9:
        /* "caller/caller.sol":950:957  uint256 */
      0x00
        /* "caller/caller.sol":976:982  callee */
      0x00
      0x00
      swap1
      sload
      swap1
      0x0100
      exp
      swap1
      div
      0xffffffffffffffffffffffffffffffffffffffff
      and
        /* "caller/caller.sol":976:987  callee.getX */
      0xffffffffffffffffffffffffffffffffffffffff
      and
      0x5197c7aa
        /* "caller/caller.sol":976:989  callee.getX() */
      mload(0x40)
      dup2
      0xffffffff
      and
      0xe0
      shl
      dup2
      mstore
      0x04
      add
      0x20
      mload(0x40)
      dup1
      dup4
      sub
      dup2
      dup7
      gas
      staticcall
      iszero
      dup1
      iszero
      tag_29
      jumpi
      returndatacopy(0x00, 0x00, returndatasize)
      revert(0x00, returndatasize)
    tag_29:
      pop
      pop
      pop
      pop
      mload(0x40)
      returndatasize
      not(0x1f)
      0x1f
      dup3
      add
      and
      dup3
      add
      dup1
      0x40
      mstore
      pop
      dup2
      add
      swap1
      tag_30
      swap2
      swap1
      tag_31
      jump	// in
    tag_30:
        /* "caller/caller.sol":969:989  return callee.getX() */
      swap1
      pop
        /* "caller/caller.sol":905:996  function getCalleeX() external view returns (uint256) {... */
      swap1
      jump	// out
        /* "caller/caller.sol":510:583  function setCalleeX(uint256 _x) external {... */
    tag_15:
        /* "caller/caller.sol":561:567  callee */
      0x00
      0x00
      swap1
      sload
      swap1
      0x0100
      exp
      swap1
      div
      0xffffffffffffffffffffffffffffffffffffffff
      and
        /* "caller/caller.sol":561:572  callee.setX */
      0xffffffffffffffffffffffffffffffffffffffff
      and
      0x4018d9aa
        /* "caller/caller.sol":573:575  _x */
      dup3
        /* "caller/caller.sol":561:576  callee.setX(_x) */
      mload(0x40)
      dup3
      0xffffffff
      and
      0xe0
      shl
      dup2
      mstore
      0x04
      add
      tag_33
      swap2
      swap1
      tag_11
      jump	// in
    tag_33:
      0x00
      mload(0x40)
      dup1
      dup4
      sub
      dup2
      0x00
      dup8
      dup1
      extcodesize
      iszero
      dup1
      iszero
      tag_34
      jumpi
      revert(0x00, 0x00)
    tag_34:
      pop
      gas
      call
      iszero
      dup1
      iszero
      tag_36
      jumpi
      returndatacopy(0x00, 0x00, returndatasize)
      revert(0x00, returndatasize)
    tag_36:
      pop
      pop
      pop
      pop
        /* "caller/caller.sol":510:583  function setCalleeX(uint256 _x) external {... */
      pop
      jump	// out
        /* "caller/caller.sol":629:740  function callAdd(uint256 a, uint256 b) external view returns (uint256) {... */
    tag_19:
        /* "caller/caller.sol":691:698  uint256 */
      0x00
        /* "caller/caller.sol":717:723  callee */
      0x00
      0x00
      swap1
      sload
      swap1
      0x0100
      exp
      swap1
      div
      0xffffffffffffffffffffffffffffffffffffffff
      and
        /* "caller/caller.sol":717:727  callee.add */
      0xffffffffffffffffffffffffffffffffffffffff
      and
      0x771602f7
        /* "caller/caller.sol":728:729  a */
      dup5
        /* "caller/caller.sol":731:732  b */
      dup5
        /* "caller/caller.sol":717:733  callee.add(a, b) */
      mload(0x40)
      dup4
      0xffffffff
      and
      0xe0
      shl
      dup2
      mstore
      0x04
      add
      tag_38
      swap3
      swap2
      swap1
      tag_39
      jump	// in
    tag_38:
      0x20
      mload(0x40)
      dup1
      dup4
      sub
      dup2
      dup7
      gas
      staticcall
      iszero
      dup1
      iszero
      tag_41
      jumpi
      returndatacopy(0x00, 0x00, returndatasize)
      revert(0x00, returndatasize)
    tag_41:
      pop
      pop
      pop
      pop
      mload(0x40)
      returndatasize
      not(0x1f)
      0x1f
      dup3
      add
      and
      dup3
      add
      dup1
      0x40
      mstore
      pop
      dup2
      add
      swap1
      tag_42
      swap2
      swap1
      tag_31
      jump	// in
    tag_42:
        /* "caller/caller.sol":710:733  return callee.add(a, b) */
      swap1
      pop
        /* "caller/caller.sol":629:740  function callAdd(uint256 a, uint256 b) external view returns (uint256) {... */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "caller/caller.sol":225:253  CalleeContract public callee */
    tag_22:
      0x00
      0x00
      swap1
      sload
      swap1
      0x0100
      exp
      swap1
      div
      0xffffffffffffffffffffffffffffffffffffffff
      and
      dup2
      jump	// out
        /* "caller/caller.sol":793:864  function callIncrementX() external {... */
    tag_26:
        /* "caller/caller.sol":838:844  callee */
      0x00
      0x00
      swap1
      sload
      swap1
      0x0100
      exp
      swap1
      div
      0xffffffffffffffffffffffffffffffffffffffff
      and
        /* "caller/caller.sol":838:855  callee.incrementX */
      0xffffffffffffffffffffffffffffffffffffffff
      and
      0x40f006be
        /* "caller/caller.sol":838:857  callee.incrementX() */
      mload(0x40)
      dup2
      0xffffffff
      and
      0xe0
      shl
      dup2
      mstore
      0x04
      add
      0x00
      mload(0x40)
      dup1
      dup4
      sub
      dup2
      0x00
      dup8
      dup1
      extcodesize
      iszero
      dup1
      iszero
      tag_44
      jumpi
      revert(0x00, 0x00)
    tag_44:
      pop
      gas
      call
      iszero
      dup1
      iszero
      tag_46
      jumpi
      returndatacopy(0x00, 0x00, returndatasize)
      revert(0x00, returndatasize)
    tag_46:
      pop
      pop
      pop
      pop
        /* "caller/caller.sol":793:864  function callIncrementX() external {... */
      jump	// out
        /* "#utility.yul":7:84   */
    tag_47:
        /* "#utility.yul":44:51   */
      0x00
        /* "#utility.yul":73:78   */
      dup2
        /* "#utility.yul":62:78   */
      swap1
      pop
        /* "#utility.yul":7:84   */
      swap2
      swap1
      pop
      jump	// out
        /* "#utility.yul":90:208   */
    tag_48:
        /* "#utility.yul":177:201   */
      tag_64
        /* "#utility.yul":195:200   */
      dup2
        /* "#utility.yul":177:201   */
      tag_47
      jump	// in
    tag_64:
        /* "#utility.yul":172:175   */
      dup3
        /* "#utility.yul":165:202   */
      mstore
        /* "#utility.yul":90:208   */
      pop
      pop
      jump	// out
        /* "#utility.yul":214:436   */
    tag_11:
        /* "#utility.yul":307:311   */
      0x00
        /* "#utility.yul":345:347   */
      0x20
        /* "#utility.yul":334:343   */
      dup3
        /* "#utility.yul":330:348   */
      add
        /* "#utility.yul":322:348   */
      swap1
      pop
        /* "#utility.yul":358:429   */
      tag_66
        /* "#utility.yul":426:427   */
      0x00
        /* "#utility.yul":415:424   */
      dup4
        /* "#utility.yul":411:428   */
      add
        /* "#utility.yul":402:408   */
      dup5
        /* "#utility.yul":358:429   */
      tag_48
      jump	// in
    tag_66:
        /* "#utility.yul":214:436   */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":523:640   */
    tag_50:
        /* "#utility.yul":632:633   */
      0x00
        /* "#utility.yul":629:630   */
      0x00
        /* "#utility.yul":622:634   */
      revert
        /* "#utility.yul":769:891   */
    tag_52:
        /* "#utility.yul":842:866   */
      tag_71
        /* "#utility.yul":860:865   */
      dup2
        /* "#utility.yul":842:866   */
      tag_47
      jump	// in
    tag_71:
        /* "#utility.yul":835:840   */
      dup2
        /* "#utility.yul":832:867   */
      eq
        /* "#utility.yul":822:885   */
      tag_72
      jumpi
        /* "#utility.yul":881:882   */
      0x00
        /* "#utility.yul":878:879   */
      0x00
        /* "#utility.yul":871:883   */
      revert
        /* "#utility.yul":822:885   */
    tag_72:
        /* "#utility.yul":769:891   */
      pop
      jump	// out
        /* "#utility.yul":897:1036   */
    tag_53:
        /* "#utility.yul":943:948   */
      0x00
        /* "#utility.yul":981:987   */
      dup2
        /* "#utility.yul":968:988   */
      calldataload
        /* "#utility.yul":959:988   */
      swap1
      pop
        /* "#utility.yul":997:1030   */
      tag_74
        /* "#utility.yul":1024:1029   */
      dup2
        /* "#utility.yul":997:1030   */
      tag_52
      jump	// in
    tag_74:
        /* "#utility.yul":897:1036   */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":1042:1371   */
    tag_14:
        /* "#utility.yul":1101:1107   */
      0x00
        /* "#utility.yul":1150:1152   */
      0x20
        /* "#utility.yul":1138:1147   */
      dup3
        /* "#utility.yul":1129:1136   */
      dup5
        /* "#utility.yul":1125:1148   */
      sub
        /* "#utility.yul":1121:1153   */
      slt
        /* "#utility.yul":1118:1237   */
      iszero
      tag_76
      jumpi
        /* "#utility.yul":1156:1235   */
      tag_77
      tag_50
      jump	// in
    tag_77:
        /* "#utility.yul":1118:1237   */
    tag_76:
        /* "#utility.yul":1276:1277   */
      0x00
        /* "#utility.yul":1301:1354   */
      tag_78
        /* "#utility.yul":1346:1353   */
      dup5
        /* "#utility.yul":1337:1343   */
      dup3
        /* "#utility.yul":1326:1335   */
      dup6
        /* "#utility.yul":1322:1344   */
      add
        /* "#utility.yul":1301:1354   */
      tag_53
      jump	// in
    tag_78:
        /* "#utility.yul":1291:1354   */
      swap2
      pop
        /* "#utility.yul":1247:1364   */
      pop
        /* "#utility.yul":1042:1371   */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":1377:1851   */
    tag_18:
        /* "#utility.yul":1445:1451   */
      0x00
        /* "#utility.yul":1453:1459   */
      0x00
        /* "#utility.yul":1502:1504   */
      0x40
        /* "#utility.yul":1490:1499   */
      dup4
        /* "#utility.yul":1481:1488   */
      dup6
        /* "#utility.yul":1477:1500   */
      sub
        /* "#utility.yul":1473:1505   */
      slt
        /* "#utility.yul":1470:1589   */
      iszero
      tag_80
      jumpi
        /* "#utility.yul":1508:1587   */
      tag_81
      tag_50
      jump	// in
    tag_81:
        /* "#utility.yul":1470:1589   */
    tag_80:
        /* "#utility.yul":1628:1629   */
      0x00
        /* "#utility.yul":1653:1706   */
      tag_82
        /* "#utility.yul":1698:1705   */
      dup6
        /* "#utility.yul":1689:1695   */
      dup3
        /* "#utility.yul":1678:1687   */
      dup7
        /* "#utility.yul":1674:1696   */
      add
        /* "#utility.yul":1653:1706   */
      tag_53
      jump	// in
    tag_82:
        /* "#utility.yul":1643:1706   */
      swap3
      pop
        /* "#utility.yul":1599:1716   */
      pop
        /* "#utility.yul":1755:1757   */
      0x20
        /* "#utility.yul":1781:1834   */
      tag_83
        /* "#utility.yul":1826:1833   */
      dup6
        /* "#utility.yul":1817:1823   */
      dup3
        /* "#utility.yul":1806:1815   */
      dup7
        /* "#utility.yul":1802:1824   */
      add
        /* "#utility.yul":1781:1834   */
      tag_53
      jump	// in
    tag_83:
        /* "#utility.yul":1771:1834   */
      swap2
      pop
        /* "#utility.yul":1726:1844   */
      pop
        /* "#utility.yul":1377:1851   */
      swap3
      pop
      swap3
      swap1
      pop
      jump	// out
        /* "#utility.yul":1857:1983   */
    tag_54:
        /* "#utility.yul":1894:1901   */
      0x00
        /* "#utility.yul":1934:1976   */
      0xffffffffffffffffffffffffffffffffffffffff
        /* "#utility.yul":1927:1932   */
      dup3
        /* "#utility.yul":1923:1977   */
      and
        /* "#utility.yul":1912:1977   */
      swap1
      pop
        /* "#utility.yul":1857:1983   */
      swap2
      swap1
      pop
      jump	// out
        /* "#utility.yul":1989:2049   */
    tag_55:
        /* "#utility.yul":2017:2020   */
      0x00
        /* "#utility.yul":2038:2043   */
      dup2
        /* "#utility.yul":2031:2043   */
      swap1
      pop
        /* "#utility.yul":1989:2049   */
      swap2
      swap1
      pop
      jump	// out
        /* "#utility.yul":2055:2197   */
    tag_56:
        /* "#utility.yul":2105:2114   */
      0x00
        /* "#utility.yul":2138:2191   */
      tag_87
        /* "#utility.yul":2156:2190   */
      tag_88
        /* "#utility.yul":2165:2189   */
      tag_89
        /* "#utility.yul":2183:2188   */
      dup5
        /* "#utility.yul":2165:2189   */
      tag_54
      jump	// in
    tag_89:
        /* "#utility.yul":2156:2190   */
      tag_55
      jump	// in
    tag_88:
        /* "#utility.yul":2138:2191   */
      tag_54
      jump	// in
    tag_87:
        /* "#utility.yul":2125:2191   */
      swap1
      pop
        /* "#utility.yul":2055:2197   */
      swap2
      swap1
      pop
      jump	// out
        /* "#utility.yul":2203:2329   */
    tag_57:
        /* "#utility.yul":2253:2262   */
      0x00
        /* "#utility.yul":2286:2323   */
      tag_91
        /* "#utility.yul":2317:2322   */
      dup3
        /* "#utility.yul":2286:2323   */
      tag_56
      jump	// in
    tag_91:
        /* "#utility.yul":2273:2323   */
      swap1
      pop
        /* "#utility.yul":2203:2329   */
      swap2
      swap1
      pop
      jump	// out
        /* "#utility.yul":2335:2483   */
    tag_58:
        /* "#utility.yul":2407:2416   */
      0x00
        /* "#utility.yul":2440:2477   */
      tag_93
        /* "#utility.yul":2471:2476   */
      dup3
        /* "#utility.yul":2440:2477   */
      tag_57
      jump	// in
    tag_93:
        /* "#utility.yul":2427:2477   */
      swap1
      pop
        /* "#utility.yul":2335:2483   */
      swap2
      swap1
      pop
      jump	// out
        /* "#utility.yul":2489:2664   */
    tag_59:
        /* "#utility.yul":2598:2657   */
      tag_95
        /* "#utility.yul":2651:2656   */
      dup2
        /* "#utility.yul":2598:2657   */
      tag_58
      jump	// in
    tag_95:
        /* "#utility.yul":2593:2596   */
      dup3
        /* "#utility.yul":2586:2658   */
      mstore
        /* "#utility.yul":2489:2664   */
      pop
      pop
      jump	// out
        /* "#utility.yul":2670:2936   */
    tag_24:
        /* "#utility.yul":2785:2789   */
      0x00
        /* "#utility.yul":2823:2825   */
      0x20
        /* "#utility.yul":2812:2821   */
      dup3
        /* "#utility.yul":2808:2826   */
      add
        /* "#utility.yul":2800:2826   */
      swap1
      pop
        /* "#utility.yul":2836:2929   */
      tag_97
        /* "#utility.yul":2926:2927   */
      0x00
        /* "#utility.yul":2915:2924   */
      dup4
        /* "#utility.yul":2911:2928   */
      add
        /* "#utility.yul":2902:2908   */
      dup5
        /* "#utility.yul":2836:2929   */
      tag_59
      jump	// in
    tag_97:
        /* "#utility.yul":2670:2936   */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":2942:3085   */
    tag_60:
        /* "#utility.yul":2999:3004   */
      0x00
        /* "#utility.yul":3030:3036   */
      dup2
        /* "#utility.yul":3024:3037   */
      mload
        /* "#utility.yul":3015:3037   */
      swap1
      pop
        /* "#utility.yul":3046:3079   */
      tag_99
        /* "#utility.yul":3073:3078   */
      dup2
        /* "#utility.yul":3046:3079   */
      tag_52
      jump	// in
    tag_99:
        /* "#utility.yul":2942:3085   */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":3091:3442   */
    tag_31:
        /* "#utility.yul":3161:3167   */
      0x00
        /* "#utility.yul":3210:3212   */
      0x20
        /* "#utility.yul":3198:3207   */
      dup3
        /* "#utility.yul":3189:3196   */
      dup5
        /* "#utility.yul":3185:3208   */
      sub
        /* "#utility.yul":3181:3213   */
      slt
        /* "#utility.yul":3178:3297   */
      iszero
      tag_101
      jumpi
        /* "#utility.yul":3216:3295   */
      tag_102
      tag_50
      jump	// in
    tag_102:
        /* "#utility.yul":3178:3297   */
    tag_101:
        /* "#utility.yul":3336:3337   */
      0x00
        /* "#utility.yul":3361:3425   */
      tag_103
        /* "#utility.yul":3417:3424   */
      dup5
        /* "#utility.yul":3408:3414   */
      dup3
        /* "#utility.yul":3397:3406   */
      dup6
        /* "#utility.yul":3393:3415   */
      add
        /* "#utility.yul":3361:3425   */
      tag_60
      jump	// in
    tag_103:
        /* "#utility.yul":3351:3425   */
      swap2
      pop
        /* "#utility.yul":3307:3435   */
      pop
        /* "#utility.yul":3091:3442   */
      swap3
      swap2
      pop
      pop
      jump	// out
        /* "#utility.yul":3448:3780   */
    tag_39:
        /* "#utility.yul":3569:3573   */
      0x00
        /* "#utility.yul":3607:3609   */
      0x40
        /* "#utility.yul":3596:3605   */
      dup3
        /* "#utility.yul":3592:3610   */
      add
        /* "#utility.yul":3584:3610   */
      swap1
      pop
        /* "#utility.yul":3620:3691   */
      tag_105
        /* "#utility.yul":3688:3689   */
      0x00
        /* "#utility.yul":3677:3686   */
      dup4
        /* "#utility.yul":3673:3690   */
      add
        /* "#utility.yul":3664:3670   */
      dup6
        /* "#utility.yul":3620:3691   */
      tag_48
      jump	// in
    tag_105:
        /* "#utility.yul":3701:3773   */
      tag_106
        /* "#utility.yul":3769:3771   */
      0x20
        /* "#utility.yul":3758:3767   */
      dup4
        /* "#utility.yul":3754:3772   */
      add
        /* "#utility.yul":3745:3751   */
      dup5
        /* "#utility.yul":3701:3773   */
      tag_48
      jump	// in
    tag_106:
        /* "#utility.yul":3448:3780   */
      swap4
      swap3
      pop
      pop
      pop
      jump	// out

    auxdata: 0xa2646970667358221220b08b57eb7ba292c65a25cd59aa57abe337696c62fefe0110dfe8d433a70b840364736f6c634300081e0033
}


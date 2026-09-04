package com.stress.repository;

import com.stress.entity.SysUser;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface UserRepository extends JpaRepository<SysUser, Long> {
    Optional<SysUser> findByUsername(String username);
    boolean existsByUsername(String username);
    Page<SysUser> findByUsernameContainingOrNicknameContaining(String username, String nickname, Pageable pageable);
}
